from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="paideia_cms",
    version="0.0.1",
    description="Custom CMS for Paideia website",
    author="Paideia",
    author_email="info@paideia.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.12",
)
