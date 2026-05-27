import zipfile
import xml.etree.ElementTree as ET

fname = '概要设计模板(1).docx'
z = zipfile.ZipFile(fname)
doc = z.read('word/document.xml')
root = ET.fromstring(doc)

nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

for p in root.iter(f'{{{nsmap["w"]}}}p'):
    style = ''
    pPr = p.find(f'{{{nsmap["w"]}}}pPr')
    if pPr is not None:
        pStyle = pPr.find(f'{{{nsmap["w"]}}}pStyle')
        if pStyle is not None:
            style = pStyle.get(f'{{{nsmap["w"]}}}val', '')

    texts = []
    for t in p.iter(f'{{{nsmap["w"]}}}t'):
        if t.text:
            texts.append(t.text)
    line = ''.join(texts)

    if line.strip():
        print(f'[{style}] {line}')
