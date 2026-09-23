:orphan:

Assessment Splitter Web App
============================

The Assessment Splitter is a static browser-based tool that takes a scanned
multi-student PDF of assessments and splits it into one PDF per assessment,
matched by QR codes embedded on each page.

.. button-link:: ./splitter/index.html
   :color: primary
   :expand:

   ➜ Launch the Assessment Splitter

The app runs entirely in your browser — no server, no upload — so scanned
student work never leaves your machine.

How it works
------------

Each assessment page carries three QR codes (top-of-center, bottom-left,
bottom-right) encoding the assessment ID. The workflow is:

1. Author the assessments in LaTeX using the provided template
2. Print, distribute, collect, and scan the completed packets as a single
   multi-page PDF
3. Open the app, drop in a YAML config listing the assessment IDs in order,
   then drop in the scanned PDF
4. Review any pages flagged for manual override, then download the split
   PDFs as a ZIP

Related resources
-----------------

- :download:`Example configuration (YAML) <_extra/splitter/examples/assessments_2026-04-27.yaml>`
- :download:`LaTeX template with embedded QR codes <_extra/splitter/examples/qrcode_assessment_template.tex>`

See the source in the repository at ``docs/source/_extra/splitter/``.
