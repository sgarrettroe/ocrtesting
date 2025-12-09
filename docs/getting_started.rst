Getting Started
===============

Installation
------------
Set up the conda environment and then install the package in developer
mode in the new environment. From the root of the project, run

.. code-block:: bash

   % conda env create -f environment.yaml
   % conda activate ocrtesting

How to Run `ocrtesting`
================================

General Chemistry
-----------------------------------------------------------------------
Set up the configuration file in a local directory, e.g.,

.. code-block:: yaml

    assessment_list:
      - '5.1'
      - '5.1'
      - '1.1'
      - '1.2'
      - '1.3'
      - '2.1'
      - '2.2'
      - '2.3'
      - '3.1'
      - '3.2'
      - '3.3'
      - '4.1'
      - '4.2'
      - '4.3'

The elements of this array are the string to search for on each page.

Then, run the code to process the scans

.. code-block:: bash

   % ocr-gchem configuration_file.yaml file_name_1.pdf file_name_2.pdf

