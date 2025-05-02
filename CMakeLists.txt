cmake_minimum_required(VERSION 3.10)
project(ezyZip)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Tìm thư viện zlib
find_package(ZLIB REQUIRED)

# Thêm các file nguồn
add_executable(ezyZip
    src/main.cpp
    src/unzipper.cpp
)

# Thêm thư mục include
target_include_directories(ezyZip PRIVATE
    ${CMAKE_SOURCE_DIR}/src
    ${ZLIB_INCLUDE_DIRS}
)

# Link với các thư viện
target_link_libraries(ezyZip PRIVATE
    ${ZLIB_LIBRARIES}
)