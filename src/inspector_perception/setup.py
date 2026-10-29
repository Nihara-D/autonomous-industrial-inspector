from setuptools import find_packages, setup

package_name = "inspector_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/perception.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Nihara Randini",
    maintainer_email="nihara@example.com",
    description="Overhead-camera colour object detection for Industrial Inspector",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "color_detector = inspector_perception.color_detector_node:main",
        ],
    },
)
