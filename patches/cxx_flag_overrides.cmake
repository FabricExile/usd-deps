if(MSVC)
    set(CMAKE_CXX_FLAGS_DEBUG_INIT "/D_DEBUG /MP8 /MTd /Zi /Ob0 /Od /RTC1 /bigobj /wd4005 /wd4065 /wd4244 /wd4267 /wd4305 /wd4605")
    set(CMAKE_CXX_FLAGS_MINSIZEREL_INIT     "/MP8 /MT /O1 /Ob1 /D NDEBUG /bigobj /wd4005 /wd4065 /wd4244 /wd4267 /wd4305 /wd4605")
    set(CMAKE_CXX_FLAGS_RELEASE_INIT        "/MP8 /MT /O2 /Ob2 /D NDEBUG /bigobj /wd4005 /wd4065 /wd4244 /wd4267 /wd4305 /wd4605")
    set(CMAKE_CXX_FLAGS_RELWITHDEBINFO_INIT "/MP8 /MT /Zi /O2 /Ob1 /D NDEBUG /bigobj /wd4005 /wd4065 /wd4244 /wd4267 /wd4305 /wd4605")
endif()

