cmake_minimum_required(VERSION 3.8)
project(jcheng_simulation_arm)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

ament_package()
