from docx import Document
from io import StringIO
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
# from pyth.plugins.rtf15.reader import Rtf15Reader
# from pyth.plugins.plaintext.writer import PlaintextWriter
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter

def convertDocxToText(path):
	document = Document(path)
	return "\n".join([para.text for para in document.paragraphs])

def convertPDFToText(path):
    rsrcmgr = PDFResourceManager()
    fake_file_handle = StringIO()

    try:
        device = TextConverter(rsrcmgr, fake_file_handle, laparams=LAParams())
    except Exception as e:
        print(e)

    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    string = fake_file_handle.getvalue()
    fake_file_handle.close()
    return string

# def convertRtfToText(path):
# 	doc = Rtf15Reader.read(open(path))
# 	return PlaintextWriter.write(doc).getvalue()