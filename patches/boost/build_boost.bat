call "C:\Program Files (x86)\Microsoft Visual Studio {{VSVERSION}}.0\VC\vcvarsall.bat" x86
 
cd {{SOURCEPATH}}
call bootstrap.bat
 
rem Most libraries can be static libs
b2 -j8 toolset=msvc-{{VSVERSION}}.0 address-model=64 architecture=x86 variant=release link=shared threading=multi runtime-link=shared --with-date_time --with-iostreams --with-program_options --with-python --with-regex --with-system --stagedir={{BUILDPATH}} stage
