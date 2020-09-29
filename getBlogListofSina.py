import sys, urllib, urllib.request as requests, re, codecs, html, pymysql, time
from bs4 import BeautifulSoup
from ConfigData import ConfigData as cd
from Blog import Blog


# 取得博文详细信息
def get_BlogDetail(strUrl):
    #retBlog = Blog(title, strUrl, publish, comment, read, picAddress, content, tag, category)
    
    request = requests.Request(strUrl)
    response = requests.urlopen(request)
    html = response.read()    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 查找包含TAG和CATEGORY的段落
    strFindList = str(soup.find_all('div', cd.patternTagDiv))
    tagList = re.findall(cd.patternTag, strFindList)
    if tagList != None and len(tagList) > 0:
        tag = (str(re.findall(cd.patternTag, strFindList)[0])[6:-2]).split(",")
    else:
        tag = []
    categoryList = re.findall(cd.patternCategory, strFindList)
    if categoryList != None and len(categoryList) > 0:
        category = (str(re.findall(cd.patternCategory, strFindList)[0])[1:-3]).split(",")
    else:
        category = [] 
    
    # 查找TITLE的段落
    strFindList = str(soup.find('title')).strip()
    title = strFindList[7:-8].split("_")[0]
    # print(title)
    
    # 查找发表时间的段落
    strFindList = str(soup.find_all('span', cd.patternTitleDetail))
    publish = str(re.findall(cd.patternPublishDetail, strFindList)[0])

    # 用Python发送API，获取JS返回值的方式获取评论数和阅读数
    comment, read = get_cr_num(strUrl, get_crDict("&aids=" + strUrl[-11:-5]))
    
    # 获得博文内容
    content = str(soup.find('div', cd.patternContent ))
   
    # 获得图像地址列表
    strFindList = soup.find_all('img', title=re.compile(title))
    picAddressList = []
    for strFind in strFindList:
        picAddress = str(re.findall(r'real_src=.+src=', str(strFind)))[12:-6].strip()[:-1]
        picAddress = picAddress.replace('&amp;', '&')
        picAddressList.append(picAddress)
    
    return Blog(title, strUrl, publish, comment, read, picAddressList, content, tag, category)

       

# 取得评论和阅读数的字典合集
# INPUT: param （&aids=02vdeu,0136nk）
# RETURN: r - 评论数； c - 阅读数
def get_crDict(param):
    url = cd.crUrl + param
    #print(url)
    
    request = requests.Request(url)
    response = requests.urlopen(request)
  
    pattern = cd.patternCR
    htmlW = str(re.findall(pattern, str(response.read()).strip())[0][:-1])

    return eval(htmlW)

# 取得评论和阅读数
# INPUT: _url （http://blog.sina.com.cn/s/blog_5922f3300101e20o.htm）
# RETURN: r - 评论数； c - 阅读数
def get_cr_num(strUrl, cr_dict):
    needFindKey = strUrl[-11:-5]
    return cr_dict[needFindKey].get('c'), cr_dict[needFindKey].get('r')


# 生成Blog文章清单，生成HTML文件
def makeBlogList():
    # 保存具体内容的待爬取URL清单
    needProcessURL = set()
    
    # 需要爬取的URL列表
    starUrlList = []
    for i in range(1,5):
        starUrlList.append(cd.strUrl + str(i) + ".html")
                   
    # 生成博客文章一览表，格式：
    # 序号 | 主题 | URL| 是否有图| 评论数/阅读数| 发表时间 | 分类| 标签| 内容
    fout = codecs.open('sina.html', 'w', encoding='utf-8')
    fout.write(cd.htmlStart)

    i=1    #  博客文章序号
    blogList = []
    for url in starUrlList:
        request = requests.Request(url, headers=cd.headers)
        response = requests.urlopen(request)
        html = response.read()
        soup = BeautifulSoup(html, 'html.parser')

        # strFindList = soup.find_all('a', href=re.compile(cd.patternALink))
        strFindList = soup.find_all('div', cd.patternDiv)

        paramCR = '&aids='
        for strFind in strFindList:
            strFind = str(strFind)
            resUrl = re.findall(cd.patternUrl, strFind)[0]
            blogList.append(get_BlogDetail(str(resUrl)))
            
    for blog in blogList:
        hasPic = cd.outPic if len(blog.picAddress) > 0 else ''
        fout.write(cd.htmlCont.format(str(i), blog.title, blog.url, blog.url, blog.picAddress,
                                      blog.comment, blog.read, blog.publish,
                                      blog.category, blog.tag,
                                      blog.content))
        i += 1    
  
    fout.write(cd.htmlEnd)
    fout.close()


# 将单条博文写入数据库
def makeTypechoData(cursor, blog):
    title = blog.title.replace("\'","&prime;")  # 博文主题
    cid =  cd.content_cid % cd.db_name  # cid和slug
    created = int(time.mktime(time.strptime(blog.publish, cd.timeFormat))) #创建和修改时间
    text = "<!--markdown-->" + blog.content.replace("\'","&prime;")  # 博文内容
    #print("\n\n\n####################\n"+text+"\n####################\n\n\n")
    authorId = 1  # 作者id
    commentsNum = int(blog.comment)  # 评论数
    views = int(blog.read)  # 阅读数
    
    try:
        sql = "INSERT INTO typecho_contents SET title='%s', slug=%s, created=%d, modified=%d, \
                text='%s', authorId=%d, type='%s', commentsNum=%d, views=%d"
        param = (title, cid, created, created, text, authorId, 'post_draft', commentsNum, views)
        sql = sql % param
        #print(sql)
        cursor.execute(sql)  
    except Exception as e:
        print("Exception is: " + str(e))
        raise e


def writeIntoTypecho():
    # 确定写入的Typecho的数据库信息
    conn = pymysql.Connect(
        host = cd.db_host,
        port = cd.db_port,
        user = cd.db_user,
        passwd = cd.db_password,
        db = cd.db_name,
        charset = cd.db_charset
    )
    cursor = conn.cursor()
    
    # 保存具体内容的待爬取URL清单
    needProcessURL = set()
    
    # 需要爬取的URL列表
    starUrlList = []
    for i in range(1,5):
        starUrlList.append(cd.strUrl + str(i) + ".html")
    
    i = 0
    for url in starUrlList:
        i += 1
        request = requests.Request(url, headers=cd.headers)
        response = requests.urlopen(request)
        html = response.read()
        soup = BeautifulSoup(html, 'html.parser')

        # strFindList = soup.find_all('a', href=re.compile(cd.patternALink))
        strFindList = soup.find_all('div', cd.patternDiv)

        #paramCR = '&aids='
        j=0
        for strFind in strFindList:
            j += 1
            strFind = str(strFind)
            resUrl = re.findall(cd.patternUrl, strFind)[0]
            try:
                makeTypechoData(cursor, get_BlogDetail(str(resUrl)))
            except Exception as e:
                print("第 %d-%d 条写入出错" % (i,j))
                print(e)
                continue
                
            else:
                print("第 %d-%d 条写入完毕" % (i,j))
        
    conn.commit()
    cursor.close()
    conn.close()
        

if __name__ == '__main__':
    #makeBlogList()
    writeIntoTypecho()

