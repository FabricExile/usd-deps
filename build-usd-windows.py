import os
import sys
import glob
import shutil
import platform
import tarfile
import zipfile
import subprocess

target = sys.argv[-1]
if target == __file__:
  target = 'all'

allowedTargets = [
  'clean',
  'all',
  'tbb', 
  'double-conversion',
  'ilmbase',
  'hdf5',
  'openexr',
  'ptex',
  'glew',
  'glut',
  'opensubdiv',
  'alembic',
]
if not target in allowedTargets:
  print """
Usage:

python make-windows.py [target]

target: %s
""" % ', '.join(allowedTargets)
  exit(1)

root = os.path.abspath(os.path.split(__file__)[0])
build = os.path.join(root, 'build')
stage = os.path.join(root, 'stage')
vsversion = '12'
vspath = r"C:\Program Files (x86)\Microsoft Visual Studio %s.0\Common7\IDE" % vsversion
msbuild = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\msbuild.exe"
if not os.path.exists(msbuild):
  raise Exception('no visual studio executable found')

fabricThirdParty = os.path.join(os.environ['FABRIC_SCENE_GRAPH_DIR'], 'ThirdParty', 'PreBuilt', 'Windows', 'x86_64', 'VS2013', 'Release')
zlibpath = os.path.join(fabricThirdParty, 'zlib', '1.2.8')
boostpath = os.path.join(fabricThirdParty, 'boost', '1.55.0')

#========================================= clean =====================================
if target in ['clean']:
  print 'removing %s' % build
  if os.path.exists(build):
    shutil.rmtree(build)
  print 'removing %s' % stage
  if os.path.exists(stage):
    shutil.rmtree(stage)
  exit(0)

#========================================= helpers =====================================

def requiresBuild(name, dependencies=[]):
  if not target in ['all', name] + dependencies:
    return False
  marker = os.path.join(build, name, '.'+name+'.marker')
  return not os.path.exists(marker)

def extractSourcePackage(name, folder, filename):
  sourcepath = os.path.join(build, name, folder)
  if not os.path.exists(sourcepath):
    filepath = os.path.join(root, 'pkgs', filename)
    if not os.path.exists(filepath):
      raise Exception('filepath '+filepath+' does not exist.')
    dest = os.path.join(build, name)
    if filepath.lower().endswith('.zip'):
      with zipfile.ZipFile(filepath, 'r') as z:
        z.extractall(dest)
    else:
      with tarfile.open(filepath) as archive:
        archive.extractall(path=dest)
    return True
  return False

def patchSourceFile(sourceFile, patchFile):
  sourceFile = os.path.join(build, sourceFile)
  patchFile = os.path.join(root, 'patches', patchFile)
  cmd = ['patch', sourceFile, patchFile]
  p = subprocess.Popen(cmd, cwd=os.path.split(sourceFile)[0])
  p.wait()

def runMSBuild(project, buildpath):
  env = {}
  env.update(os.environ)
  env['PATH'] = env['PATH'] + os.pathsep + vspath
  env['VCTargetsPath'] = r'C:\Program Files (x86)\MSBuild\Microsoft.Cpp\v4.0\V%s0' % vsversion
  cmd = [msbuild, project, '/t:build', '/p:Configuration=Release', '/p:Configuration=Release', '/p:Platform=x64']
  p = subprocess.Popen(cmd, cwd=buildpath, env=env)
  p.wait()

def runCMake(name, folder, projects, flags={}, env={}, subfolder='build'):
  sourcepath = os.path.join(build, name, folder)
  buildpath = os.path.join(build, name, subfolder)
  if not os.path.exists(buildpath):
    os.makedirs(buildpath)

  env.update(os.environ)

  cmd = ['cmake', "-G", "Visual Studio %s Win64" % vsversion, sourcepath]
  for flag in flags:
    cmd += ['-D%s=%s' % (flag, flags[flag])]
  p = subprocess.Popen(cmd, cwd=buildpath, env=env)
  p.wait()

  for project in projects:
    runMSBuild('%s.vcxproj' % project, buildpath)

  marker = os.path.join(build, name, '.'+name+'.marker')
  open(marker, 'wb').write('done')

# def runScons(name, folder):
#   sourcepath = os.path.join(build, name, folder)
#   buildpath = os.path.join(build, name, 'build')
#   if not os.path.exists(buildpath):
#     os.makedirs(buildpath)

#   env = {}
#   env.update(os.environ)
#   env['MSVC_VERSION'] = '%s.0' % vsversion
#   cmd = ['scons', '-f', os.path.join(sourcepath, 'SConstruct')]
#   print cmd
#   p = subprocess.Popen(cmd, cwd=buildpath)
#   p.wait()

  # marker = os.path.join(build, name, '.'+name+'.marker')
  # open(marker, 'wb').write('done')

def stageResults(name, includeFolders, libraryFolders):
  sources = {
    'include': [includeFolders, ['h', 'hpp']],
    'lib': [libraryFolders, ['lib']]
  }

  for key in sources:
    folders = sources[key][0]
    filters = sources[key][1]
    for folder in folders:
      for root, dirs, files in os.walk(folder):
        for f in files:
          if not f.rpartition('.')[2].lower() in filters:
            continue
          path = os.path.join(root, f)
          print "Installing %s" % path
          if key == 'lib':
            targetpath = os.path.join(stage, 'lib', f)
          else:
            relpath = os.path.relpath(path, folder)
            targetpath = os.path.join(stage, key, name, relpath)
          targetdir = os.path.split(targetpath)[0]
          if not os.path.exists(targetdir):
            os.makedirs(targetdir)
          shutil.copyfile(path, targetpath)

#========================================= tbb =====================================

if requiresBuild('tbb', ['opensubdiv']):
  # tbb on windows uses a drop from https://github.com/wjakob/tbb/tree/tbb43u6
  extractSourcePackage('tbb', 'tbb-tbb43u6', 'tbb-tbb43u6.tgz')
  runCMake('tbb', 'tbb-tbb43u6', ['tbbmalloc_static', 'tbbmalloc_proxy_static', 'tbb_static'])

  stageResults('tbb', [
    os.path.join(build, 'tbb', 'tbb-tbb43u6', 'include')
    ], [
    os.path.join(build, 'tbb', 'build', 'Release')
    ])

#==================================== double conversion ============================

if requiresBuild('double-conversion'):
  extractSourcePackage('double-conversion', 'double-conversion-1.1.5', 'double-conversion-1.1.5.tar.gz')
  runCMake('double-conversion', 'double-conversion-1.1.5', ['ALL_BUILD'])

  stageResults('double-conversion', [
    os.path.join(build, 'double-conversion', 'double-conversion-1.1.5', 'src')
    ], [
    os.path.join(build, 'double-conversion', 'build', 'src', 'Release')
    ])

#========================================== boost ====================================

# we are going to use boost from the fabric software thirdparty folder

#========================================= ilmbase ===================================

if requiresBuild('ilmbase', ['openexr']):
  extractSourcePackage('ilmbase', 'ilmbase-2.2.0', 'ilmbase-2.2.0.tar.gz')
  runCMake('ilmbase', 'ilmbase-2.2.0', ['ALL_BUILD'], flags={'BUILD_SHARED_LIBS': 'off'})

  stageResults('ilmbase', [
    os.path.join(build, 'ilmbase', 'ilmbase-2.2.0')
    ], [
    os.path.join(build, 'ilmbase', 'build')
    ])

#========================================== hdf5 =====================================

if requiresBuild('hdf5', ['alembic']):
  extractSourcePackage('hdf5', 'hdf5-1.8.9', 'hdf5-1.8.9.tar.bz2')
  runCMake('hdf5', 'hdf5-1.8.9', ['src/hdf5', 'hl/src/hdf5_hl'], flags={'BUILD_SHARED_LIBS': 'off', 'HDF5_BUILD_HL_LIB': 'on'})

  stageResults('hdf5', [
    os.path.join(build, 'hdf5', 'hdf5-1.8.9', 'src'),
    os.path.join(build, 'hdf5', 'hdf5-1.8.9', 'hl', 'src'),
    os.path.join(build, 'hdf5', 'build')
    ], [
    os.path.join(build, 'hdf5', 'build', 'bin', 'Release')
    ])

#========================================= openexr ===================================
  
if requiresBuild('openexr'):
  ilmbasesourcepath = os.path.join(build, 'ilmbase', 'ilmbase-2.2.0')
  ilmbasebuildpath = os.path.join(build, 'ilmbase', 'build')
  if extractSourcePackage('openexr', 'openexr-2.2.0', 'openexr-2.2.0.tar.gz'):
    patchSourceFile('openexr/openexr-2.2.0/CMakeLists.txt', 'openexr/CMakeLists.txt.patch')

  runCMake('openexr', 'openexr-2.2.0', ['IlmImf/IlmImf', 'IlmImf/dwaLookups', 'IlmImfUtil/IlmImfUtil'], 
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      'ZLIB_LIBRARY': os.path.join(zlibpath, 'lib', 'zlibstatic.lib'),
      'ILMBASE_INCLUDE_DIR': ilmbasesourcepath,
      'ILMBASE_LIBRARY_DIR': ilmbasebuildpath,
    })

  stageResults('openexr', [
    os.path.join(build, 'openexr', 'openexr-2.2.0')
    ], [
    os.path.join(build, 'openexr', 'build')
    ])

#========================================== ptex =====================================

if requiresBuild('ptex', ['opensubdiv']):
  extractSourcePackage('ptex', 'ptex-2.0.41', 'ptex-2.0.41.zip')
  runCMake('ptex', 'ptex-2.0.41/src', ['ptex/Ptex_static'],
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      'ZLIB_LIBRARY': os.path.join(zlibpath, 'lib', 'zlibstatic.lib'),
    })

  stageResults('ptex', [
    os.path.join(build, 'ptex', 'ptex-2.0.41', 'src', 'ptex')
    ], [
    os.path.join(build, 'ptex', 'build', 'ptex', 'Release')
    ])

#========================================== glew =====================================

if requiresBuild('glew', ['opensubdiv']):
  extractSourcePackage('glew', 'glew-1.13.0', 'glew-1.13.0.tgz')
  buildpath = os.path.join(build, 'glew', 'glew-1.13.0', 'build', 'vc%s' % vsversion)
  runMSBuild('glew_static.vcxproj', buildpath)

  marker = os.path.join(build, 'glew', '.glew.marker')
  open(marker, 'wb').write('done')

  stageResults('glew', [
    os.path.join(build, 'glew', 'glew-1.13.0', 'include')
    ], [
    os.path.join(build, 'glew', 'glew-1.13.0', 'lib')
    ])

#======================================== opensubdiv =================================

if requiresBuild('opensubdiv'):
  extractSourcePackage('opensubdiv', 'OpenSubdiv-3_0_5', 'OpenSubdiv-3_0_5.tar.gz')

  #glewsourcepath = os.path.join(build, 'glew', 'glew-1.13.0')
  ptexsourcepath = os.path.join(build, 'ptex', 'ptex-2.0.41/src')
  ptexbuildpath = os.path.join(build, 'ptex', 'build')
  tbbsourcepath = os.path.join(build, 'tbb', 'tbb-tbb43u6')
  tbbbuildpath = os.path.join(build, 'tbb', 'build')

  runCMake('opensubdiv', 'OpenSubdiv-3_0_5', ['opensubdiv/osd_static_cpu'],
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      # 'ZLIB_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      # 'ZLIB_LIBRARY': os.path.join(zlibpath, 'lib', 'zlibstatic.lib'),
      'PTEX_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      'PTEX_LIBRARY': os.path.join(ptexbuildpath, 'ptex', 'Release', 'Ptex.lib'),
      # 'GLEW_INCLUDE_DIR': os.path.join(glewsourcepath, 'include'),
      # 'GLEW_LIBRARY': os.path.join(glewsourcepath, 'lib', 'Release', 'x64', 'glew32s.lib'),
      'TBB_INCLUDE_DIR': os.path.join(tbbsourcepath, 'include'),
      'TBB_LIBRARIES': os.path.join(tbbbuildpath, 'Release'),
      'NO_LIB': 'off',
      'NO_EXAMPLES': 'on',
      'NO_TUTORIALS': 'on',
      'NO_REGRESSION': 'off',
      'NO_MAYA': 'on',
      'NO_PTEX': 'off',
      'NO_DOC': 'on',
      'NO_OMP': 'on',
      'NO_TBB': 'off',
      'NO_CUDA': 'on',
      'NO_OPENCL': 'on',
      'NO_CLEW': 'on',
      'NO_OPENGL': 'on',
      'NO_DX': 'on',
      'NO_TESTS': 'on',
      'NO_GLTESTS': 'on',
    })

  stageResults('opensubdiv', [
    os.path.join(build, 'opensubdiv', 'OpenSubdiv-3_0_5', 'opensubdiv')
    ], [
    os.path.join(build, 'opensubdiv', 'build', 'lib', 'Release')
    ])

if requiresBuild('alembic'):
  if extractSourcePackage('alembic', 'alembic-1.5.8', 'alembic-1.5.8.tar.gz'):
    patchSourceFile('alembic/alembic-1.5.8/CMakeLists.txt', 'alembic/CMakeLists.txt.patch')
    patchSourceFile('alembic/alembic-1.5.8/lib/Alembic/Abc/Foundation.h', 'alembic/Foundation.h.patch')

  runCMake('alembic', 'alembic-1.5.8', [
      'lib/Alembic/Abc/AlembicAbc',
      'lib/Alembic/AbcCollection/AlembicAbcCollection',
      'lib/Alembic/AbcCoreAbstract/AlembicAbcCoreAbstract',
      'lib/Alembic/AbcCoreFactory/AlembicAbcCoreFactory',
      'lib/Alembic/AbcCoreHDF5/AlembicAbcCoreHDF5',
      'lib/Alembic/AbcCoreOgawa/AlembicAbcCoreOgawa',
      'lib/Alembic/AbcGeom/AlembicAbcGeom',
      'lib/Alembic/AbcMaterial/AlembicAbcMaterial',
      'lib/Alembic/Ogawa/AlembicOgawa',
      'lib/Alembic/Util/AlembicUtil',
    ],
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      'ZLIB_LIBRARY': os.path.join(zlibpath, 'lib', 'zlibstatic.lib'),
      'BOOST_ROOT': boostpath,
      'ALEMBIC_ILMBASE_INCLUDE_DIRECTORY': os.path.join(stage, 'include', 'ilmbase'),
      'ILMBASE_ROOT': stage,
      'ILMBASE_LIBRARY_DIR': os.path.join(stage, 'lib'),
      'ALEMBIC_ILMBASE_HALF_LIB': os.path.join(stage, 'lib', 'Half.lib'),
      'ALEMBIC_ILMBASE_IEX_LIB': os.path.join(stage, 'lib', 'Iex.lib'),
      'ALEMBIC_ILMBASE_ILMTHREAD_LIB': os.path.join(stage, 'lib', 'IlmThread-2_2.lib'),
      'ALEMBIC_ILMBASE_IMATH_LIB': os.path.join(stage, 'lib', 'Imath-2_2.lib'),
      'ALEMBIC_HDF5_INCLUDE_PATH': os.path.join(stage, 'include', 'hdf5'),
      'ALEMBIC_HDF5_LIBS': os.path.join(stage, 'lib', 'hdf5.lib'),
      'USE_PYILMBASE': 'off',
      'USE_PRMAN': 'off',
      'USE_ARNOLD': 'off',
      'USE_MAYA': 'off',
      'USE_PYALEMBIC': 'off',
      })

  stageResults('alembic', [
    os.path.join(build, 'alembic', 'alembic-1.5.8', 'lib', 'Alembic')
    ], [
    os.path.join(build, 'alembic', 'build', 'lib')
    ])

# not needed:
# oiio-Release-1.5.20.tar.gz ?
# flex-2.5.39.tar.bz2
# PyOpenGL-3.0.2.tar.gz
# Python-2.7.12.tgz
# pyilmbase-2.2.0.tar.gz
# pyside-qt4.8+1.2.2.tar.bz2
# pyside-tools-0.2.15.tar.gz
# qt-everywhere-opensource-src-4.8.6.tar.gz
# shiboken-1.2.2.tar.bz2
