import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re

fn = [f for f in os.listdir('.') if '総務課' in f][0]
print("File:", fn)

def find_cc(vals):
    for v in vals:
        if v is None: continue
        s = str(v).strip()
        match = re.search(r'\b(1\d{3}|2\d{3}|3\d{3}|4\d{3}|5\d{3}|6\d{3}|7\d{3}|8\d{3}|9\d{3})\b', s)
        if match: return True
        match = re.search(r'\b(1412\d{6})\b', s)
        if match: return True
    return False

try:
    with zipfile.ZipFile(fn, 'r') as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            ss_tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in ss_tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
                strings.append(si.text)
        
        wb_tree = ET.fromstring(z.read('xl/workbook.xml'))
        rels_tree = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        
        for sheet in wb_tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
            name = sheet.get('name')
            rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            rel = rels_tree.find(f'.//*[@Id="{rid}"]')
            if rel is None: continue
            
            target = rel.get('Target')
            if target.startswith('/'): target = target[1:]
            elif not target.startswith('xl/'): target = 'xl/' + target
            
            try: ws_xml = z.read(target)
            except: continue
                
            ws_tree = ET.fromstring(ws_xml)
            print(f"--- Sheet: {name} ---")
            
            found_cc_count = 0
            for row_count, row in enumerate(ws_tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')):
                vals = []
                for c in row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                    v = c.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                    if v is not None and v.text is not None:
                        if c.get('t') == 's':
                            try: vals.append(strings[int(v.text)])
                            except: vals.append(v.text)
                        else: vals.append(v.text)
                    else:
                        inline = c.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                        vals.append(inline.text if inline is not None else None)
                
                if find_cc(vals):
                    print(f"Row {row_count}: {vals[:10]}")
                    found_cc_count += 1
                    if found_cc_count > 20:
                        print("... truncating ...")
                        break
                        
except Exception as e:
    import traceback
    traceback.print_exc()
