from setuptools import find_packages, setup

package_name = "inspector_pick_place"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Nihara Randini",
    maintainer_email="nihara@example.com",
    description="Automated pick-and-place for Industrial Inspector",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "pick_place_node = inspector_pick_place.pick_place_node:main",
        ],
    },
)
