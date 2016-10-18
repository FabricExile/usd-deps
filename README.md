# usd-deps

Building the dependencies for Pixar's [USD](https://github.com/PixarAnimationStudios/USD) library is somewhat tricky.  `usd-deps` attempts to automate this for you as much as possible.

## License

This package is licensed under a three-clause BSD license, contained in the file [LICENSE.txt](/LICENSE.txt).

## Features

- In addition to the required dependencies, also build Alembic so the USD Alembic plugin can be built.

- Optionally allows a specific build of GCC to be used to build the dependencies rather than the system default.  This is useful, for instance, when the default compiler is not the version required to build USD itself, and we want to avoid ABI issues that would result from the dependencies being built with a different version of GCC.

## Important Notes

- This is currently Linux-only since USD is Linux-only

- This does not work for the v0.7.0 tag of USD since there are issues with the CMake configuration.  As of this writing it works with the dev branch of USD.

- **We accept the Qt open source license for you.  If you are not OK with the Qt open source license restrictions then you should not use this package.**

- A few packages need to be installed from the OS package manager for the build to work.  On CentOS 6 I needed to:

```
sudo yum install cmake libxml2-devel libxslt-devel gstreamer-plugins-base-devel bzip2-devel sqlite-devel openssl-devel libGL-devel libGLU-devel libXrandr-devel libXcursor-devel libXinerama-devel freeglut-devel libXmu-devel libXi-devel libpng-devel libjpeg-devel giflib-devel libtiff-devel
```

- We don't compile pylimbase or the Python support for Alembic because, well, we couldn't get them to compile.

## Usage

`usd-deps` uses [git lfs](https://git-lfs.github.com) to include copies of the binary packages it builds; you will need to install it if you haven't already.  Then, in your clone of this repository, run `git lfs pull` to download the binary packages.

To build the USD dependencies, run:

```
make -j4 PREFIX=/opt/usd-deps [GCC_ROOT=/opt/gcc-4.8] [SPLIT=1]
```

The required `PREFIX` argument is the directory into which the USD dependencies should be installed.

The optional `GCC_ROOT` argument, if set, causes the built to use a build of GCC below the given directory.  It also sets `LD_LIBRARY_PATH` to the corresponding subdirectories so that executables that are part of the build can be run during the build process.

The optional `SPLIT` argument, if set, causes the dependencies to be installed into separate directories below `PREFIX`.  This is mostly useful for testing, since each dependency can then be more easily cleaned before being rebuilt.

The `make` command will generate all of the dependencies for USD, as well as a script `$PREFIX/bin/build-usd.sh` which will build and install USD using these dependencies.  To see the usage of `build-usd.sh`, simply run it without any arguments.
