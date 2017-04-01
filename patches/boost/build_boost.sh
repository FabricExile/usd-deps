#!/bin/bash

cd {{SOURCEPATH}}
chmod +x bootstrap.sh
./bootstrap.sh
 
# Most libraries can be static libs
./b2 -j8 cflags=-fPIC address-model=64 architecture=x86 variant=release link=static threading=multi runtime-link=static --with-date_time --with-iostreams --with-program_options --with-python --with-regex --with-system --stagedir={{BUILDPATH}} stage
