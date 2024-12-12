import subprocess
import sys
import os
import pathlib
import logging
import pypdf

# set up logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-24s %(levelname)-8s %(message)s')
logger = logging.getLogger('ocrtesting.process_scans_gchem')
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.INFO)



def reverse_pdf(pdfin) -> None:
    reader = pypdf.PdfReader(pdfin)
    writer = pypdf.PdfWriter()

    logging.info('\t...reversing pages')
    out_name = pathlib.Path(pdfin).stem + '_reversed.pdf'
    logging.debug(f'output name : {out_name}')

    n_pages = reader.get_num_pages()
    tmp = [int(num) for num in range(n_pages)]
    tmp.reverse()
    logging.debug(f'Page list = {tmp}' + '\n')

    logging.debug(f'pypdf found {n_pages} pages')
    for p in tmp:
        writer.add_page(reader.pages[p])

    with open(out_name, "wb") as fp:
        writer.write(fp)


def main() -> None:
    """Process pdf scans to separate assessment files"""
    logging.info(f'Arguments in ({len(sys.argv)}): {sys.argv}')

    for item in sys.argv[1:]:
        if not os.path.exists(item):
            raise FileNotFoundError(f'Cannot locate file {item}.')

        logging.info(f'Processing {item}:')
        reverse_pdf(item)
        logging.info('\t...done')

    return None


if __name__ == '__main__':
    sys.exit(main())
