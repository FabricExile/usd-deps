import os
import re
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
  'zlib', 
  'tbb', 
  'boost', 
  'double-conversion',
  'ilmbase',
  'hdf5',
  'openexr',
  'ptex',
  'opensubdiv',
  'alembic',
  'usd-static',
  'usd-dynamic',
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
vsversion = '14'
vspath = r"C:\Program Files (x86)\Microsoft Visual Studio %s.0\Common7\IDE" % vsversion
msbuild = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\msbuild.exe"
ucrtpath = r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.10240.0'

if not os.path.exists(msbuild):
  raise Exception('msbuildpath not found')
if not os.path.exists(ucrtpath):
  raise Exception('ucrtpath not found')

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

def requiresBuild(name, dependencies=[], excludeFromAllTarget=False):
  targets = [name] + dependencies
  if not excludeFromAllTarget:
    targets += ['all']
  if not target in targets:
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

def patchSourceFile(sourceFile, patchFile, throw=True):
  if not os.path.isabs(sourceFile):
    sourceFile = os.path.join(build, sourceFile)
  if not os.path.isabs(patchFile):
    patchFile = os.path.join(root, 'patches', patchFile)

  cmd = ['patch', '-N', sourceFile, patchFile]
  p = subprocess.Popen(cmd, cwd=os.path.split(sourceFile)[0])
  p.wait()
  if p.returncode != 0 and throw:
    raise Exception('patchSourceFile failed')

def insertCMakeProlog(sourcepath, name='default'):
  if not os.path.isabs(sourcepath):
    sourcepath = os.path.join(build, sourcepath)
  sourcefile = os.path.join(sourcepath, 'CMakeLists.txt')
  content = None
  with open(sourcefile, 'rb') as f:
    content = f.read()

  prolog = """
set(CMAKE_USER_MAKE_RULES_OVERRIDE
    ${CMAKE_CURRENT_SOURCE_DIR}/c_flag_overrides_%s.cmake)
set(CMAKE_USER_MAKE_RULES_OVERRIDE_CXX
    ${CMAKE_CURRENT_SOURCE_DIR}/cxx_flag_overrides_%s.cmake)
""" % (name, name)

  if not content.startswith(prolog):
    with open(sourcefile, 'wb') as f:
      f.write(prolog + content)

  for override in [
    'c_flag_overrides_%s.cmake' % name,
    'cxx_flag_overrides_%s.cmake' % name,
    ]:
    shutil.copyfile(os.path.join(root, 'patches', override), os.path.join(sourcepath, override))

def runMSBuild(project, buildpath, configuration='Release'):
  env = {}
  env.update(os.environ)
  env['PATH'] = env['PATH'] + os.pathsep + vspath
  env['VCTargetsPath'] = r'C:\Program Files (x86)\MSBuild\Microsoft.Cpp\v4.0\V%s0' % vsversion
  cmd = [msbuild, project, '/t:build', '/p:Configuration=%s' % configuration, '/p:Platform=x64']
  p = subprocess.Popen(cmd, cwd=buildpath, env=env)
  p.wait()
  if p.returncode != 0:
    raise Exception('runMSBuild failed')

def runCMake(name, folder, projects, flags={}, env={}, subfolder='build', configuration='Release', cmakeProlog='default'):
  sourcepath = folder
  if not os.path.isabs(sourcepath):
    sourcepath = os.path.join(build, name, sourcepath)
  buildpath = os.path.join(build, name, subfolder)
  if not os.path.exists(buildpath):
    os.makedirs(buildpath)

  env.update(os.environ)

  # if cmakeProlog:
  #   insertCMakeProlog(sourcepath, name=cmakeProlog)

  # cmd = ['cmake', "--trace", "--debug-output", "-G", "Visual Studio %s Win64" % vsversion, sourcepath]
  # cmd = ['cmake', "-G", "Visual Studio %s Win64" % vsversion, sourcepath]
  cmd = ['cmake', "-G", "Visual Studio %s" % vsversion, sourcepath]
  for flag in flags:
    cmd += ['-D%s=%s' % (flag, flags[flag])]

  # ensure 64 bit generator
  cmd += ['-DCMAKE_GENERATOR_PLATFORM=x64']

  p = subprocess.Popen(cmd, cwd=buildpath, env=env)
  p.wait()
  if p.returncode != 0:
    raise Exception('runCMake failed')

  for project in projects:
    runMSBuild('%s.vcxproj' % project, buildpath, configuration=configuration)

  marker = os.path.join(build, name, '.'+name+'.marker')
  open(marker, 'wb').write('done')

def stageResults(name, includeFolders, libraryFolders):
  sources = {
    'include': [includeFolders, ['h', 'hpp', 'ipp']],
    'lib': [libraryFolders, ['lib', 'dll', 'so', 'dylib']]
  }

  for key in sources:
    folders = sources[key][0]
    filters = sources[key][1]
    for folder in folders:
      for r, dirs, files in os.walk(folder):
        for f in files:
          if not f.rpartition('.')[2].lower() in filters:
            continue
          path = os.path.join(r, f)
          if key == 'lib':
            targetpath = os.path.join(stage, 'lib', f)
          else:
            relpath = os.path.relpath(path, folder)
            targetpath = os.path.join(stage, key, name, relpath)
          targetdir = os.path.split(targetpath)[0]
          if not os.path.exists(targetdir):
            os.makedirs(targetdir)
          print "Installing %s" % targetpath
          shutil.copyfile(path, targetpath)

#========================================= zlib ====================================

if requiresBuild('zlib'):
  extractSourcePackage('zlib', 'zlib-1.2.11', 'zlib-1.2.11.zip')
  runCMake('zlib', 'zlib-1.2.11', ['zlibstatic'], cmakeProlog='minimal')

  stageResults('zlib', [
    os.path.join(build, 'zlib', 'zlib-1.2.11'),
    os.path.join(build, 'zlib', 'build')
    ], [
    os.path.join(build, 'zlib', 'build', 'Release')
    ])

#========================================= boost ====================================

if requiresBuild('boost'):
  sourcepath = os.path.join(build, 'boost', 'boost_1_63_0')
  buildpath = os.path.join(build, 'boost', 'build')

  env = {}
  env.update(os.environ)
  env['PATH'] += r';C:\Program Files (x86)\Microsoft Visual Studio %s.0\VC\bin' % vsversion

  extractSourcePackage('boost', 'boost_1_63_0', 'boost_1_63_0.tar.bz2')
  if platform.system() == 'Windows':

    content = None
    with open(os.path.join(root, 'patches', 'boost', 'build_boost.bat'), 'rb') as f:
      content = f.read()

    content = content.replace('{{VSVERSION}}', vsversion)
    content = content.replace('{{SOURCEPATH}}', sourcepath)
    content = content.replace('{{BUILDPATH}}', buildpath)
    content = content.replace('{{STAGEPATH}}', stage)

    with open(os.path.join(sourcepath, 'build_boost.bat'), 'wb') as f:
      f.write(content)

    p = subprocess.Popen([os.path.join(sourcepath, 'build_boost.bat')])
    p.wait()
    if p.returncode != 0:
      raise Exception('building boost failed')

  else:
    raise Exception('implement running b2 some other way')
    # you may want to look into the build_boost.bat in patches

  marker = os.path.join(build, 'boost', '.boost.marker')
  open(marker, 'wb').write('done')

  stageResults('boost', [
    os.path.join(build, 'boost', 'boost_1_63_0', 'boost')
    ], [
    os.path.join(build, 'boost', 'build', 'lib')
    ])

#========================================= tbb =====================================

if requiresBuild('tbb', ['opensubdiv']):
  # tbb on windows uses a drop from https://github.com/wjakob/tbb/tree/tbb43u6
  if extractSourcePackage('tbb', 'tbb-tbb43u6', 'tbb-tbb43u6.tgz'):
    patchSourceFile('tbb/tbb-tbb43u6/include/tbb/tbb_config.h', 'tbb/tbb_config.h.patch')

  runCMake('tbb', 'tbb-tbb43u6', ['tbbmalloc', 'tbbmalloc_proxy', 'tbb'])

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

if requiresBuild('hdf5', ['alembic'], excludeFromAllTarget=True):
  if extractSourcePackage('hdf5', 'hdf5-1.8.9', 'hdf5-1.8.9.tar.bz2'):
    patchSourceFile('hdf5/hdf5-1.8.9/config/cmake/ConfigureChecks.cmake', 'hdf5/ConfigureChecks.cmake.patch')

  runCMake('hdf5', 'hdf5-1.8.9', ['src/hdf5', 'hl/src/hdf5_hl'], flags={'BUILD_SHARED_LIBS': 'off', 'HDF5_BUILD_HL_LIB': 'on', 'H5_HAVE_TIMEZONE': 'off'})

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
      'ZLIB_INCLUDE_DIR': os.path.join(stage, 'include', 'zlib'),
      'ZLIB_LIBRARY': os.path.join(stage, 'lib', 'zlibstatic.lib'),
      'ILMBASE_INCLUDE_DIR': ilmbasesourcepath,
      'ILMBASE_LIBRARY_DIR': ilmbasebuildpath,
    })

  stageResults('openexr', [
    os.path.join(build, 'openexr', 'openexr-2.2.0')
    ], [
    os.path.join(build, 'openexr', 'build')
    ])

#========================================== ptex =====================================

if requiresBuild('ptex', ['opensubdiv'], excludeFromAllTarget=True):
  extractSourcePackage('ptex', 'ptex-2.0.41', 'ptex-2.0.41.zip')
  runCMake('ptex', 'ptex-2.0.41/src', ['ptex/Ptex_static'],
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(stage, 'include', 'zlib'),
      'ZLIB_LIBRARY': os.path.join(stage, 'lib', 'zlibstatic.lib'),
    })

  stageResults('ptex', [
    os.path.join(build, 'ptex', 'ptex-2.0.41', 'src', 'ptex')
    ], [
    os.path.join(build, 'ptex', 'build', 'ptex', 'Release')
    ])

#======================================== opensubdiv =================================

if requiresBuild('opensubdiv', excludeFromAllTarget=True):
  extractSourcePackage('opensubdiv', 'OpenSubdiv-3_0_5', 'OpenSubdiv-3_0_5.tar.gz')

  ptexsourcepath = os.path.join(build, 'ptex', 'ptex-2.0.41/src')
  ptexbuildpath = os.path.join(build, 'ptex', 'build')

  runCMake('opensubdiv', 'OpenSubdiv-3_0_5', ['opensubdiv/osd_static_cpu'],
    flags={
      'BUILD_SHARED_LIBS': 'off', 
      'ZLIB_INCLUDE_DIR': os.path.join(stage, 'include', 'zlib'),
      'ZLIB_LIBRARY': os.path.join(stage, 'lib', 'zlibstatic.lib'),
      'PTEX_INCLUDE_DIR': os.path.join(stage, 'include'),
      'PTEX_LIBRARY': os.path.join(ptexbuildpath, 'ptex', 'Release', 'Ptex.lib'),
      'TBB_INCLUDE_DIR': os.path.join(stage, 'include', 'tbb'),
      'TBB_LIBRARIES': os.path.join(stage, 'lib'),

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

if requiresBuild('alembic', excludeFromAllTarget=True):
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
      'ZLIB_INCLUDE_DIR': os.path.join(stage, 'include', 'zlib'),
      'ZLIB_LIBRARY': os.path.join(stage, 'lib', 'zlibstatic.lib'),
      'BOOST_INCLUDEDIR': os.path.join(stage, 'include'),
      'BOOST_LIBRARYDIR': os.path.join(stage, 'lib'),
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

#========================================   usd    =================================

if requiresBuild('usd-static', excludeFromAllTarget=True):

  sourcepath = os.path.join(root, 'USD')
  if not os.path.exists(sourcepath):
    raise Exception('Need to clone USD to %s' % sourcepath)

  # replace the cmakelists file
  shutil.copyfile(os.path.join(root, 'patches', 'USD', 'CMakeLists.txt'), os.path.join(sourcepath, 'CMakeLists.txt'))
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'usd', 'lib', 'sdf', 'layer.h'), 'usd/sdf.layer.h.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'base', 'lib', 'vt', 'value.h'), 'usd/vt.value.h.patch', throw=False)

  # STATIC BUILD =============================================================================

  includePath = os.path.join(build, 'USD', 'build', 'include')
  for foldername in ['base', 'usd', 'imaging', 'usdImaging']:
    folder = os.path.join(root, 'USD', 'pxr', foldername, 'lib')
    for r, dirs, files in os.walk(folder):
      for f in files:
        if not f.rpartition('.')[2].lower() in ['h']:
          continue
        path = os.path.join(r, f)
        relpath = os.path.relpath(path, folder)
        abspath = os.path.join(includePath, 'pxr', foldername, relpath)
        absfolder = os.path.split(abspath)[0]
        if not os.path.exists(absfolder):
          os.makedirs(absfolder)
        shutil.copy(path, abspath)

  runCMake('USD', sourcepath, ['usd_static'],
    flags = {
      'BOOST_INCLUDEDIR': os.path.join(stage, 'include'),
      'BOOST_LIBRARYDIR': os.path.join(stage, 'lib'),
      'TBB_INCLUDE_DIR': os.path.join(stage, 'include', 'tbb'),
      'TBB_LIBRARIES': os.path.join(stage, 'lib'),
      'OPENEXR_INCLUDE_DIR': os.path.join(stage, 'include'),
      'OPENEXR_LIBRARY_DIR': os.path.join(stage, 'lib'),
      'ILMBASE_INCLUDE_DIR': os.path.join(stage, 'include', 'ilmbase'),
      'ILMBASE_LIBRARY_DIR': os.path.join(stage, 'lib'),

      'PXR_USE_NAMESPACES': 'off',
    })

  stageResults('usd', [
    os.path.join(build, 'USD', 'build', 'include')
    ], [
    os.path.join(build, 'USD', 'build', 'Release')
    ])

  marker = os.path.join(build, 'USD', '.usd-static.marker')
  open(marker, 'wb').write('done')

  # END STATIC BUILD =========================================================================

if requiresBuild('usd-dynamic', excludeFromAllTarget=False):

  sourcepath = os.path.join(root, 'USD')
  if not os.path.exists(sourcepath):
    raise Exception('Need to clone USD to %s' % sourcepath)

  # replace the cmakelists file
  patchSourceFile(os.path.join(root, 'USD', 'cmake', 'defaults', 'Packages.cmake'), 'USD/Packages.cmake.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'cmake', 'macros', 'Public.cmake'), 'USD/Public.cmake.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'usd', 'lib', 'sdf', 'layer.h'), 'USD/sdf.layer.h.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'usd', 'lib', 'sdf', 'textFileFormat.cpp'), 'USD/textFileFormat.cpp.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'base', 'lib', 'arch', 'fileSystem.cpp'), 'USD/fileSystem.cpp.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'base', 'lib', 'vt', 'value.h'), 'USD/vt.value.h.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'base', 'lib', 'plug', 'CMakeLists.txt'), 'USD/plug.CMakeLists.txt.patch', throw=False)
  patchSourceFile(os.path.join(root, 'USD', 'pxr', 'usd', 'CMakeLists.txt'), 'USD/usd.CMakeLists.txt.patch', throw=False)

  # DYNAMIC BUILD ========================================================================

  # tbbDir = os.path.join(os.environ['FABRIC_SCENE_GRAPH_DIR'], 'ThirdParty', 'PreBuilt', 'Windows', 'x86_64', 'tbb')

  runCMake('USD', sourcepath, [
      'INSTALL',
      # 'pxr/base/lib/arch/arch',
      # 'pxr/base/lib/gf/gf',
      # 'pxr/base/lib/js/js',
      # 'pxr/base/lib/plug/plug',
      # 'pxr/base/lib/tf/tf',
      # 'pxr/base/lib/tracelite/tracelite',
      # 'pxr/base/lib/vt/vt',
      # 'pxr/base/lib/work/work',
      # 'pxr/usd/lib/ar/ar',
      # 'pxr/usd/lib/kind/kind',
      # 'pxr/usd/lib/pcp/pcp',
      # 'pxr/usd/lib/sdf/sdf',
      # 'pxr/usd/lib/usd/usd',
      # 'pxr/usd/lib/usdGeom/usdGeom',
      # 'pxr/usd/lib/usdHydra/usdHydra',
      # 'pxr/usd/lib/usdRi/usdRi',
      # 'pxr/usd/lib/usdShade/usdShade',
      # 'pxr/usd/lib/usdUI/usdUI',
      # 'pxr/usd/lib/usdUtils/usdUtils',
    ],
    flags = {
      'BOOST_INCLUDEDIR': os.path.join(stage, 'include'),
      'BOOST_LIBRARYDIR': os.path.join(stage, 'lib'),
      'TBB_INCLUDE_DIR': os.path.join(stage, 'include', 'tbb'),
      'TBB_LIBRARIES': os.path.join(stage, 'lib'),
      'TBB_LIBRARY': os.path.join(stage, 'lib', 'lib'),
      'OPENEXR_INCLUDE_DIR': os.path.join(stage, 'include'),
      'OPENEXR_LIBRARY_DIR': os.path.join(stage, 'lib'),
      'OPENEXR_Half_LIBRARY': os.path.join(stage, 'lib', 'Half.lib'),

      'PXR_STRICT_BUILD_MODE': 'off',
      'PXR_LIB_PREFIX': '',
      'PXR_VALIDATE_GENERATED_CODE': 'off',
      'PXR_BUILD_TESTS': 'off',
      'PXR_BUILD_IMAGING': 'off',
      'PXR_BUILD_USD_IMAGING': 'off',
      'PXR_BUILD_KATANA_PLUGIN': 'off',
      'PXR_BUILD_MAYA_PLUGIN': 'off',
      'PXR_BUILD_ALEMBIC_PLUGIN': 'off',
      'PXR_ENABLE_MULTIVERSE_SUPPORT': 'off',
      'PXR_MAYA_TBB_BUG_WORKAROUND': 'off',
      'PXR_ENABLE_NAMESPACES': 'off',

      'PXR_INSTALL_LOCATION': stage,
      'CMAKE_INSTALL_PREFIX': stage,

      # 'CMAKE_BUILD_TYPE': 'RELWITHDEBINFO',
    },
    configuration='RelWithDebInfo')

  marker = os.path.join(build, 'USD', '.usd-dynamic.marker')
  open(marker, 'wb').write('done')

  # END DYNAMIC BUILD ====================================================================

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
