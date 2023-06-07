import datetime
import difflib
import time
import uuid

from flask import Flask, render_template, request, make_response,send_file
from werkzeug.utils import secure_filename
import sqlite3
import os
from whoosh.fields import TEXT, SchemaClass
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.highlight import PinpointFragmenter
from whoosh.query import Term, compound
from readfile import readfile

class ArticleSchema(SchemaClass):
    title = TEXT(stored=True)
    content = TEXT(stored=True)
    id = TEXT(stored=True)
    date = TEXT(stored=True)
    filename=TEXT(stored=True)
    lowtitle=TEXT(stored=True)
    lowcontent=TEXT(stored=True)
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/upload/'
con=sqlite3.connect('file.db',check_same_thread=False)
cursors=con.cursor()
cursors.execute('''
   create  table  if not exists  filedata(
      filename varchar (400),
      create_date  varchar(100),
      id varchar(200)
   )
''')
con.commit()

@app.route('/')
def index():  # put application's code here
    k=[]
    for item in open('input.txt',encoding='utf8'):
        k.append(item.replace('\n',''))

    return render_template('search.html',k=k)


@app.route('/upload',methods=['GET','POST'])
def  upload():
    if request.method=='POST':
      date=request.form['date']
      f = request.files['fi']
      if date==datetime.datetime.now().strftime('%Y-%m-%d'):

          id=str(uuid.uuid1())
          filetype=f.filename.split('.')[1]
          f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(id+'.'+filetype)))
          cursors.execute("insert into filedata values(?,?,?)", (f.filename, date, id))
          con.commit()
          cursors.execute('select * from filedata')
          schema = ArticleSchema()
          ix = create_in("indexdir", schema, indexname='article_index')
          writer = ix.writer()
          path = os.path.abspath('.') + '\\static\\upload'
          filelists=[]
          for root, dirs, files in os.walk(path):
              for filename in files:
                  filelists.append(filename.split('.')[0])
          for obj in cursors.fetchall():
              if obj[2] in filelists:
                  filedir = root + '\\{0}'.format(obj[2]+'.'+obj[0].split('.')[1])
                  print(filedir,obj[2]+obj[0].split('.')[1])
                  writer.add_document(title=str(obj[0]),lowtitle=str(obj[0]).split('.')[0].lower(),id=obj[2],filename=obj[2]+'.'+obj[0].split('.')[1],date=obj[1],content=str(readfile(filedir)),lowcontent=str(readfile(filedir)).lower())
          writer.commit()

          return 'ok'
      else:
          return 'fail'

@app.route('/result')
def  result():
    kw=request.args.get('kw').lower()
    if kw==None:
        return render_template('result.html', kw=kw, data=[])
    f1=open('input.txt','a',encoding='utf8')
    f1.write('{0}\n'.format(kw))
    f1.close()
    ix = open_dir("indexdir", indexname='article_index')
    with ix.searcher() as searcher:
        # query = MultifieldParser(['title','content'], ix.schema).parse("游戏")
        # query = QueryParser(["content", 'author'], ix.schema).parse(query)
        seg_list =[]
        seg_list.append(kw)
        author_query = [Term('title', seg) for seg in seg_list]
        content_query = [Term('content', seg) for seg in seg_list]
        query = compound.Or([compound.Or(author_query), compound.Or(content_query)])
        results = searcher.search(query)
        results.fragmenter = PinpointFragmenter(surround=20, maxchars=30)
        data=[]
        for s in results:
            #print(22,s.get('lowtitle'))

            if kw in s.get('lowtitle'):
                filename='<b class="match">{0}</b>'.format(s.get('lowtitle'))
            else:
                filename=s.get('lowtitle')
            score = difflib.SequenceMatcher(None, kw, s.get('title').split('.')[0]).quick_ratio()
            #print(score,filename)
            o={}
            o.setdefault('score',score)
            o.setdefault('filename',s.get('filename'))
            o.setdefault('title', filename)
            o.setdefault('filetype', s.get('title').split('.')[1])
            o.setdefault('date_time', s.get('date'))
            o.setdefault('acter', 'xyz')
            o.setdefault('content', s.highlights('content') if s.highlights('content') else '')
            data.append(o)



    return render_template('result.html',kw=kw,data=sorted(data, key=lambda x: x['score'], reverse=True))


@app.route('/read')
def read():
    filename = request.args.get('filename')
    thisdate = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    f = open(os.path.abspath('.') + '\\static\\history.txt', 'a', encoding='utf8')
    f.write("{0},{1}\n".format(thisdate, filename))
    f.flush()


    path = os.path.abspath('.') + '\\static\\upload\\'+filename
    #return send_file(open(path, "rb").read(), as_attachment=False)
    if str(path).split('.')[0].lower() in['txt','pdf']:
        file_data = open(path, "rb").read()
        response = make_response(file_data)
        res=response.headers['Content-Type'] = '*/*'
    else:
        res=send_file(path)
    return  res



if __name__ == '__main__':
    app.run(debug=True)
