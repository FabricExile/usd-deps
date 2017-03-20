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
  'opensubdiv',
]
if not target in allowedTargets:
  print """
Usage:

python make-windows.py [target]

target: %s
""" % ', '.join(allowedTargets)
  exit(1)

root = os.path.abspath(os.path.split(__file__)[0])
build = os.path.join(root, '.build')
vsversion = '12'
vspath = r"C:\Program Files (x86)\Microsoft Visual Studio %s.0\Common7\IDE" % vsversion
msbuild = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\msbuild.exe"
if not os.path.exists(msbuild):
  raise Exception('no visual studio executable found')

fabricThirdParty = os.path.join(os.environ['FABRIC_SCENE_GRAPH_DIR'], 'ThirdParty', 'PreBuilt', 'Windows', 'x86_64', 'VS2013', 'Release')
zlibpath = os.path.join(fabricThirdParty, 'zlib', '1.2.8')

#========================================= clean =====================================
if target in ['clean']:
  print 'removing %s' % build
  if os.path.exists(build):
    shutil.rmtree(build)
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
  print cmd
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

def runCMake(name, folder, projects, flags={}, env={}):
  sourcepath = os.path.join(build, name, folder)
  buildpath = os.path.join(build, name, 'build')
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

#========================================= tbb =====================================

if requiresBuild('tbb'):
  # tbb on windows uses a drop from https://github.com/wjakob/tbb/tree/tbb43u6
  extractSourcePackage('tbb', 'tbb-tbb43u6', 'tbb-tbb43u6.tgz')
  runCMake('tbb', 'tbb-tbb43u6', ['tbbmalloc_static', 'tbbmalloc_proxy_static', 'tbb_static'])

#==================================== double conversion ============================

if requiresBuild('double-conversion'):
  extractSourcePackage('double-conversion', 'double-conversion-1.1.5', 'double-conversion-1.1.5.tar.gz')
  runCMake('double-conversion', 'double-conversion-1.1.5', ['ALL_BUILD'])

#========================================== boost ====================================
# we are going to use boost from the fabric software thirdparty folder

#========================================= ilmbase ===================================

if requiresBuild('ilmbase', ['openexr']):
  extractSourcePackage('ilmbase', 'ilmbase-2.2.0', 'ilmbase-2.2.0.tar.gz')
  runCMake('ilmbase', 'ilmbase-2.2.0', ['ALL_BUILD'], flags={'BUILD_SHARED_LIBS': 'off'})

#========================================== hdf5 =====================================

if requiresBuild('hdf5', ['alembic']):
  extractSourcePackage('hdf5', 'hdf5-1.8.9', 'hdf5-1.8.9.tar.bz2')
  runCMake('hdf5', 'hdf5-1.8.9', ['ALL_BUILD'], flags={'BUILD_SHARED_LIBS': 'off'})

#========================================= openexr ===================================

if requiresBuild('openexr'):
  ilmbasesourcepath = os.path.join(build, 'ilmbase', 'ilmbase-2.2.0')
  ilmbasebuildpath = os.path.join(build, 'ilmbase', 'build')
  if extractSourcePackage('openexr', 'openexr-2.2.0', 'openexr-2.2.0.tar.gz'):
    patchSourceFile('openexr/openexr-2.2.0/CMakeLists.txt', 'openexr/CMakeLists.txt.patch')

  runCMake('openexr', 'openexr-2.2.0', ['ALL_BUILD'], 
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      'ZLIB_LIBRARY': os.path.join(zlibpath, 'lib', 'zlibstatic.lib'),
      'ILMBASE_INCLUDE_DIR': ilmbasesourcepath,
      'ILMBASE_LIBRARY_DIR': ilmbasebuildpath,
    })

#========================================== ptex =====================================

if requiresBuild('ptex', ['opensubdiv']):
  extractSourcePackage('ptex', 'ptex-2.0.41', 'ptex-2.0.41.zip')
  runCMake('ptex', 'ptex-2.0.41/src', ['ptex/Ptex_static'],
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(zlibpath, 'include'),
      'ZLIB_LIBRARY': os.path.join(zlibpath, 'lib', 'zlibstatic.lib'),
    })

#========================================== glew =====================================

if requiresBuild('glew', ['opensubdiv']):
  extractSourcePackage('glew', 'glew-1.13.0', 'glew-1.13.0.tgz')
  buildpath = os.path.join(build, 'glew', 'glew-1.13.0', 'build', 'vc%s' % vsversion)
  runMSBuild('glew_static.vcxproj', buildpath)

  marker = os.path.join(build, 'glew', '.glew.marker')
  open(marker, 'wb').write('done')

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

# alembic-1.5.8.tar.gz

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
