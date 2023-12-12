#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec  9 09:10:56 2022

@author: SGR
"""

import process_scans3
import os
import logging
#set up logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

pdfin = 'SGR_v1_014.pdf'
pdfin = 'SGR_v1_015.pdf'
os.chdir('ocrtxt')
d = process_scans3.buildpagelist3(pdfin)

