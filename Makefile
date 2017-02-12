ifdef GCC_ROOT
  GCC_CC?=$(GCC_ROOT)/bin/gcc
  GCC_CXX?=$(GCC_ROOT)/bin/g++
  GCC_LIB=$(GCC_ROOT)/lib64
  export LD_LIBRARY_PATH=$(GCC_ROOT)/lib64
  unexport GCC_ROOT
else
  GCC_CC=cc
  GCC_CXX=c++
  GCC_LIB=
endif

ifndef PREFIX
  $(error PREFIX is not set)
endif
unexport PREFIX

ifdef SPLIT
  dstDir=$(PREFIX)/$(1)
  unexport SPLIT
else
  dstDir=$(PREFIX)
endif

buildStamp=$(call dstDir,$(1))/.stamp-$(1)

unpackTarGZ=\
	rm -rf build/$(1) && \
	  mkdir -p build && \
	  cd build && \
	  tar zxf ../pkgs/$(1).tar.gz

unpackZip=\
	rm -rf build/$(1) && \
	  mkdir -p build && \
	  cd build && \
	  unzip ../pkgs/$(1).zip

unpackTGZ=\
	rm -rf build/$(1) && \
	  mkdir -p build && \
	  cd build && \
	  tar zxf ../pkgs/$(1).tgz

unpackTarBZ2=\
	rm -rf build/$(1) && \
	  mkdir -p build && \
	  cd build && \
	  tar jxf ../pkgs/$(1).tar.bz2

ifdef SPLIT
cleanDstDir=rm -rf $(call dstDir,$(1))
else
cleanDstDir=
endif

ifdef PYTHON_PREFIX
USD_PYTHON_PREFIX=$(PYTHON_PREFIX)
else
USD_PYTHON_PREFIX=$(call dstDir,python)
endif

touchBuildStamp=\
	touch $(call buildStamp,$(1))

makeCmd=\
	$(MAKE) \
	CC=$(GCC_CC) \
	CXX=$(GCC_CXX) \

configureCmd=\
	CC=$(GCC_CC) \
	CXX=$(GCC_CXX) \
	./configure \
	--prefix=$(call dstDir,$(1)) \

cmakeCmd=\
	cmake \
	-G"Unix Makefiles" \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_C_COMPILER=$(GCC_CC) \
	-DCMAKE_CXX_COMPILER=$(GCC_CXX) \
	-DCMAKE_INSTALL_PREFIX=$(call dstDir,$(1)) \

# Extract the number of jobs so it can be passed to boost compilation
MAKE_PID:=$(shell echo $$PPID)
JOB_FLAG:=$(filter -j%, $(subst -j ,-j,$(shell ps T | grep "^\s*$(MAKE_PID).*$(MAKE)")))
JOBS:=$(subst -j,,$(JOB_FLAG))

PKGS=\
	ilmbase \
	openexr \
	python \
	PyOpenGL \
	boost \
	glew \
	hdf5 \
	alembic \
	tbb \
	double-conversion \
	oiio \
	OpenSubdiv \
	ptex \
	qt \
	shiboken \
	pyside \
	pyside-tools \
	flex \

BUILD=$(call dstDir,build-usd)/bin/build-usd.sh

all: $(PKGS) $(BUILD)

.PHONY: all $(PKGS)

phonyPkg=$(1): $$(call buildStamp,$(1))

$(foreach pkg,$(PKGS),$(eval $(call phonyPkg,$(pkg))))

$(call buildStamp,ilmbase):
	$(call unpackTarGZ,ilmbase-2.2.0)
	cd build/ilmbase-2.2.0 && \
	  $(call cmakeCmd,ilmbase) \
	  -DNAMESPACE_VERSIONING:BOOLEAN=OFF \
	  .
	$(call cleanDsrDir,ilmbase)
	cd build/ilmbase-2.2.0 && $(MAKE) install
	touch $(call buildStamp,ilmbase)

$(call buildStamp,openexr): $(call buildStamp,ilmbase)
	$(call unpackTarGZ,openexr-2.2.0)
	cd build/openexr-2.2.0 && \
	  $(call cmakeCmd,openexr) \
	  -DNAMESPACE_VERSIONING:BOOLEAN=OFF \
	  -DILMBASE_PACKAGE_PREFIX:PATH=$(call dstDir,ilmbase) \
	  .
	$(call cleanDstDir,openexr)
	cd build/openexr-2.2.0 && $(MAKE) install
	touch $(call buildStamp,openexr)

$(call buildStamp,python):
ifndef PYTHON_PREFIX
	$(call unpackTGZ,Python-2.7.12)
	cd build/Python-2.7.12 && \
	  LDFLAGS="-Wl,-rpath,$(call dstDir,python)/lib" \
	  $(call configureCmd,python) \
	  --enable-shared \
	  --enable-unicode=ucs4
	$(call cleanDstDir,python)
	cd build/Python-2.7.12 && \
	  CC=$(GCC_CC) \
	  CXX=$(GCC_CXX) \
	  LDFLAGS="-Wl,-rpath,$(call dstDir,python)/lib" \
	  $(MAKE) install
endif
	$(call touchBuildStamp,python)

#$(call buildStamp,pyilmbase): $(call buildStamp,ilmbase) $(call buildStamp,boost)
#	$(call unpackTarGZ,pyilmbase-2.2.0)
#	cd build/pyilmbase-2.2.0 && \
#	  PKG_BUILD_PATH=$(call dstDir,ilmbase)/lib/pkgconfig \
#	  LD_LIBRARY_PATH=$(call dstDir,ilmbase)/lib:$(call dstDir,boost)/lib:$$LD_LIBRARY_PATH \
#	  PATH=$(call dstDir,python)/bin:$$PATH \
#	  $(call configureCmd,pyilmbase) \
#	  --with-boost-include-dir=$(call dstDir,boost)/include \
#	  --with-boost-lib-dir=$(call dstDir,boost)/lib \
#	  --with-pic
#	cd build/pyilmbase-2.2.0 && \
#	  LD_LIBRARY_PATH=$(call dstDir,ilmbase)/lib:$(call dstDir,boost)/lib:$$LD_LIBRARY_PATH \
#	  $(MAKE)
#	$(call cleanDstDir,pyilmbase)
#	cd build/pyilmbase-2.2.0 && \
#	  LD_LIBRARY_PATH=$(call dstDir,ilmbase)/lib:$(call dstDir,boost)/lib:$$LD_LIBRARY_PATH \
#	  $(MAKE) install
#	$(call touchBuildStamp,pyilmbase)

$(call buildStamp,boost): $(call buildStamp,python)
	$(call unpackTarBZ2,boost_1_55_0)
	echo 'using gcc : 4.8 : $(GCC_CXX) ;' >>build/boost_1_55_0/tools/build/v2/user-config.jam
	cd build/boost_1_55_0 && ./bootstrap.sh --with-python=$(USD_PYTHON_PREFIX)/bin/python
	$(call cleanDirDir,boost)
	cd build/boost_1_55_0 \
	  && ./b2 \
	    --toolset=gcc-4.8 \
	    --prefix=$(call dstDir,boost) \
	    $(JOB_FLAG)\
	    install
	$(call touchBuildStamp,boost)

$(call buildStamp,alembic): $(call buildStamp,boost) $(call buildStamp,ilmbase) $(call buildStamp,hdf5) $(call buildStamp,openexr) $(call buildStamp,glew)
	$(call unpackTarGZ,alembic-1.5.8)
	cd build/alembic-1.5.8 && patch -p1 <../../patches/alembic/01-CMAKE_INSTALL_PREFIX.patch
	cd build/alembic-1.5.8 && \
	  $(call cmakeCmd,alembic) \
	  -DCMAKE_CXX_FLAGS="-std=c++11 -I$(call dstDir,glew)/include -L$(call dstDir,glew)/lib64" \
	  -DBUILD_SHARED_LIBS:BOOL=ON \
	  -DBOOST_ROOT:STRING=$(call dstDir,boost) \
	  -DBOOST_INCLUDEDIR:STRING=$(call dstDir,boost)/include \
	  -DBOOST_LIBRARYDIR:STRING=$(call dstDir,boost)/lib \
	  -DILMBASE_ROOT=$(call dstDir,ilmbase) \
	  -DHDF5_ROOT=$(call dstDir,hdf5) \
	  -DUSE_PYALEMBIC:BOOLEAN=OFF \
	  .
	cd build/alembic-1.5.8 && $(MAKE)
	$(call cleanDstDir,alembic)
	cd build/alembic-1.5.8 && $(MAKE) install
	$(call touchBuildStamp,alembic)

$(call buildStamp,glew):
	$(call unpackTGZ,glew-1.13.0)
	$(call cleanDstDir,glew)
	cd build/glew-1.13.0 && \
	  $(makeCmd) \
	  DESTDIR=$(call dstDir,glew) \
	  GLEW_PREFIX= \
	  GLEW_DEST= \
	  install
	$(call touchBuildStamp,glew)

$(call buildStamp,flex):
	$(call unpackTarBZ2,flex-2.5.39)
	cd build/flex-2.5.39 && $(call configureCmd,flex)
	$(call cleanDstDir,hd5)
	cd build/flex-2.5.39 && $(MAKE) install
	$(call touchBuildStamp,flex)

$(call buildStamp,hdf5):
	$(call unpackTarBZ2,hdf5-1.8.9)
	cd build/hdf5-1.8.9 && $(call configureCmd,hdf5)
	$(call cleanDstDir,hd5)
	cd build/hdf5-1.8.9 && $(MAKE) install
	$(call touchBuildStamp,hdf5)

$(call buildStamp,tbb):
	$(call unpackTGZ,tbb43_20150611oss_lin)
	$(call cleanDstDir,tbb)
	mkdir -p $(call dstDir,tbb)/include
	cp -a build/tbb43_20150611oss/include/* $(call dstDir,tbb)/include/
	mkdir -p $(call dstDir,tbb)/lib
	cp -a build/tbb43_20150611oss/lib/intel64/gcc4.4/* $(call dstDir,tbb)/lib/
	$(call touchBuildStamp,tbb)

$(call buildStamp,double-conversion):
	$(call unpackTarGZ,double-conversion-1.1.5)
	cd build/double-conversion-1.1.5 && \
	  $(call cmakeCmd,double-conversion) \
	  -DBUILD_SHARED_LIBS:BOOL=ON \
  	  .
	$(call cleanDstDir,double-conversion)
	cd build/double-conversion-1.1.5 && $(MAKE) install
	$(call touchBuildStamp,double-conversion)

$(call buildStamp,oiio): $(call buildStamp,ilmbase) $(call buildStamp,openexr) $(call buildStamp,boost) $(call buildStamp,qt)
	$(call unpackTarGZ,oiio-Release-1.5.20)
	cd build/oiio-Release-1.5.20 && \
	  $(call cmakeCmd,oiio) \
	  -DILMBASE_HOME=$(call dstDir,ilmbase) \
	  -DOPENEXR_HOME=$(call dstDir,openexr) \
	  -DBOOST_ROOT=$(call dstDir,boost) \
	  -DQT_QMAKE_EXECUTABLE=$(call dstDir,qt)/bin/qmake \
	  .
	$(call cleanDstDir,oiio)
	cd build/oiio-Release-1.5.20 && $(MAKE) install
	mkdir -p $(call dstDir,oiio)/lib/python2.7/site-packages/
	mv $(call dstDir,oiio)/lib/python/site-packages/OpenImageIO.so $(call dstDir,oiio)/lib/python2.7/site-packages/
	rmdir $(call dstDir,oiio)/lib/python/site-packages
	rmdir $(call dstDir,oiio)/lib/python
	$(call touchBuildStamp,oiio)

$(call buildStamp,OpenSubdiv): $(call buildStamp,glew)
	$(call unpackTarGZ,OpenSubdiv-3_0_5)
	cd build/OpenSubdiv-3_0_5 && \
	  $(call cmakeCmd,OpenSubdiv) \
	  -DGLEW_LOCATION=$(call dstDir,glew) \
	  .
	$(call cleanDstDir,OpenSubdiv)
	cd build/OpenSubdiv-3_0_5 && $(MAKE) install
	ln -s $(call dstDir,OpenSubdiv)/include/opensubdiv $(call dstDir,OpenSubdiv)/include/opensubdiv3
	$(call touchBuildStamp,OpenSubdiv)

$(call buildStamp,ptex):
	$(call unpackZip,ptex-2.0.41)
	$(call cleanDstDir,ptex)
	cd build/ptex-2.0.41/src && $(call makeCmd)
	mkdir -p $(call dstDir,ptex)
	cp -a build/ptex-2.0.41/install/* $(call dstDir,ptex)/
	$(call touchBuildStamp,ptex)

$(call buildStamp,qt):
	$(call unpackTarGZ,qt-everywhere-opensource-src-4.8.6)
	cd build/qt-everywhere-opensource-src-4.8.6 && \
	  MAKEFLAGS= \
	  LD=$(GCC_CXX) \
	  $(call configureCmd,qt) \
	  --opensource \
	  --confirm-license
	cd build/qt-everywhere-opensource-src-4.8.6 && $(MAKE)
	$(call cleanDstDir,qt)
	cd build/qt-everywhere-opensource-src-4.8.6 && $(MAKE) install
	$(call touchBuildStamp,qt)

$(call buildStamp,pyside-tools): $(call buildStamp,pyside)
	$(call unpackTarGZ,pyside-tools-0.2.15)
	cd build/pyside-tools-0.2.15 && \
	  $(call cmakeCmd,pyside-tools) \
	  .
	$(call cleanDstDir,pyside-tools)
	cd build/pyside-tools-0.2.15 && \
	  $(MAKE) install
	$(call touchBuildStamp,pyside-tools)

$(call buildStamp,pyside): $(call buildStamp,qt) $(call buildStamp,shiboken)
	$(call unpackTarBZ2,pyside-qt4.8+1.2.2)
	cd build/pyside-qt4.8+1.2.2 && \
	  CMAKE_PREFIX_PATH=$(call dstDir,shiboken)/lib/cmake/Shiboken-1.2.2 \
	  $(call cmakeCmd,pyside) \
	  -DQT_QMAKE_EXECUTABLE=$(call dstDir,qt)/bin/qmake \
	  .
	$(call cleanDstDir,pyside)
	cd build/pyside-qt4.8+1.2.2 && \
	  LD_LIBRARY_PATH=$$LD_LIBRARY_PATH:$(call dstDir,qt)/lib \
	  $(MAKE) install
	$(call touchBuildStamp,pyside)

$(call buildStamp,shiboken): $(call buildStamp,python) $(call buildStamp,qt)
	$(call unpackTarBZ2,shiboken-1.2.2)
	mkdir -p build/shiboken-1.2.2/build
	cd build/shiboken-1.2.2/build && \
	  $(call cmakeCmd,shiboken) \
	  -DPYTHON_EXECUTABLE:FILEPATH=$(USD_PYTHON_PREFIX)/bin/python \
	  -DPYTHON_LIBRARY=$(USD_PYTHON_PREFIX)/lib \
	  -DPYTHON_INCLUDE_DIR=$(USD_PYTHON_PREFIX)/include/python2.7 \
	  -DQT_QMAKE_EXECUTABLE=$(call dstDir,qt)/bin/qmake \
	  ..
	$(call cleanDstDir,shiboken)
	cd build/shiboken-1.2.2/build && $(MAKE) install
	$(call touchBuildStamp,shiboken)

$(call buildStamp,PyOpenGL): $(call buildStamp,python)
	$(call unpackTarGZ,PyOpenGL-3.0.2)
	cd build/PyOpenGL-3.0.2 && \
	  CC=$(GCC_CC) \
	  CXX=$(GCC_CXX) \
	  PYTHONPATH="$$PYTHONPATH:$(call dstDir,python)/lib/python2.7/site-packages" \
	  $(USD_PYTHON_PREFIX)/bin/python \
	  setup.py \
	  install \
	  --prefix $(call dstDir,python)
	$(call touchBuildStamp,PyOpenGL)

define BUILD_SCRIPT
#!/bin/sh

if [ -z "$$1" -o -z "$$2" -o -z "$$3" ]; then
  echo "Usage: $$0 <USD source dir> <build dir> <install dir> [<make options>]"
  echo "Example: $$0 . build /opt/pixar/usd"
  exit 1
fi

USD_DIR="$$1"; shift
if [ ! -e "$$USD_DIR" ]; then
  echo "USD directory '$$USD_DIR' does not exist, exiting"
  exit 1
fi
USD_DIR="$$(readlink -e $$USD_DIR)"

BUILD_DIR="$$1"; shift
if [ -e "$$BUILD_DIR" ]; then
  echo "Build directory '$$BUILD_DIR' already exists, exiting"
  exit 1
fi

INSTALL_DIR="$$1"; shift

export PATH="$(call dstDir,pyside-tools)/bin:$$PATH"
export LD_LIBRARY_PATH="$(USD_PYTHON_PREFIX)/lib:$(call dstDir,shiboken)/lib:$(GCC_LIB):$$LD_LIBRARY_PATH"
export PYTHONPATH="$(call dstDir,python)/lib/python2.7/site-packages:$$PYTHON_PATH"

   mkdir $$BUILD_DIR \
&& cd $$BUILD_DIR \
&& \
HDF5_ROOT=$(call dstDir,hdf5) \
cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=$(GCC_CC) \
  -DCMAKE_CXX_COMPILER=$(GCC_CXX) \
  -DCMAKE_INSTALL_PREFIX="$$INSTALL_DIR" \
  -DCMAKE_BUILD_TYPE=Release \
  -DPXR_BUILD_MAYA_PLUGIN=1 \
  -DBOOST_ROOT=$(call dstDir,boost) \
  -DTBB_tbb_LIBRARY=$(call dstDir,tbb)/lib/libtbb.so \
  -DTBB_INCLUDE_DIRS=$(call dstDir,tbb)/include \
  -DOPENEXR_LOCATION=$(call dstDir,openexr) \
  -DQT_QMAKE_EXECUTABLE=$(call dstDir,qt)/bin/qmake \
  -DPYTHON_EXECUTABLE:FILEPATH=$(USD_PYTHON_PREFIX)/bin/python \
  -DPYTHON_LIBRARY=$(USD_PYTHON_PREFIX)/lib/libpython2.7.so \
  -DPYTHON_INCLUDE_DIR=$(USD_PYTHON_PREFIX)/include/python2.7 \
  -DDOUBLE_CONVERSION_LIBRARY=$(call dstDir,double-conversion)/lib/libdouble-conversion.so \
  -DDOUBLE_CONVERSION_INCLUDE_DIR=$(call dstDir,double-conversion)/include/double-conversion \
  -DOIIO_BASE_DIR=$(call dstDir,oiio) \
  -DOIIO_BINARIES=$(call dstDir,oiio)/bin \
  -DOIIO_INCLUDE_DIRS=$(call dstDir,oiio)/include \
  -DOIIO_LIBRARIES=$(call dstDir,oiio)/lib/libOpenImageIO.so \
  -DGLEW_INCLUDE_DIR=$(call dstDir,glew)/include/GL \
  -DGLEW_LIBRARY=$(call dstDir,glew)/lib64/libGLEW.a \
  -DOPENSUBDIV_ROOT_DIR=$(call dstDir,OpenSubdiv) \
  -DOPENSUBDIV_INCLUDE_DIR=$(call dstDir,OpenSubdiv)/include/opensubdiv \
  -DOPENSUBDIV_LIBRARIES=$(call dstDir,OpenSubdiv)/lib \
  -DPTEX_INCLUDE_DIR=$(call dstDir,ptex)/include/ \
  -DPTEX_LIBRARY=$(call dstDir,ptex)/lib/libPtex.a \
  -DPYSIDERCC4BINARY=$(call dstDir,pyside)/bin/pyside-rcc \
  -DPYSIDEUIC4BINARY=$(call dstDir,pyside)/bin/pyside-uic \
  -DFLEX_EXECUTABLE=$(call dstDir,flex)/bin/flex \
  -DPXR_BUILD_ALEMBIC_PLUGIN=ON \
  -DALEMBIC_DIR=$(call dstDir,alembic) \
  $$USD_DIR \
&& make "$$@" install \
&& ( [ -f $$INSTALL_DIR/plugin/usdAbc.so ] && mv -f $$INSTALL_DIR/plugin/usdAbc.so $$INSTALL_DIR/lib/libusdAbc.so ) \
&& ( [ -d $$INSTALL_DIR/plugin/usdAbc ] && rm -rf $$INSTALL_DIR/share/usd/plugins/usdAbc/ && mv $$INSTALL_DIR/plugin/usdAbc $$INSTALL_DIR/share/usd/plugins )
endef
export BUILD_SCRIPT

$(BUILD): $(PKGS)
	mkdir -p $(dir $(BUILD))
	echo "$$BUILD_SCRIPT" >$(BUILD)
	chmod +x $(BUILD)
