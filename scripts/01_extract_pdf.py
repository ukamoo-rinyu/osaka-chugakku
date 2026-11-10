import pdfplumber, json, sys
pdf=pdfplumber.open(sys.argv[1])
rows=[]; cur=[None,None,None]
for i,p in enumerate(pdf.pages):
    for tb in p.extract_tables():
        for r in tb:
            if r[0]=='区名': continue
            if len(r)!=4: print('WARN',i+1,r); continue
            for k in range(3):
                if r[k]: cur[k]=r[k].replace(' ','').replace('\n','')
            rows.append({'page':i+1,'ku':cur[0],'chu':cur[1],'sho':cur[2],'text':r[3]})
json.dump(rows,open('raw.json','w'),ensure_ascii=False,indent=1)
print(len(rows))
