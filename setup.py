from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [l.strip() for l in f if l.strip() and not l.startswith("#")]

setup(
    name="paideia_cms",
    version="1.0.0",
    description="AI-powered multilingual headless CMS on Frappe",
    author="PDCMS",
    author_email="dev@pdcms.io",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.12",
)
