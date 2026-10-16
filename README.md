# 我的书架

在线地址：<https://bk.6-66.cc/>

五个板块的阅读目录，用来形成判断，不是一份堆出来的书单。板块顺序是：宇宙与自然、三观修养、社会、政治、商业。当前 377 本。星级只有 5、4、3，表示这本书对判断有多值得读，不改变阅读顺序。

代码和书目说明以 [MIT](LICENSE) 授权。书本身的版权仍归作者和出版社。

## 本地打开

直接打开 `public/index.html`，或在仓库根目录运行：

```bash
python3 serve.py
```

页面在 <http://127.0.0.1:8791/> 。意见反馈和这个本地服务写在一起。不要占用 8765 端口。

## 目录

```
wode-shujia/
├── serve.py              本地静态服务和反馈接口
├── notes/candidates/     收书时的来源摘记，不进页面
└── public/               站点根目录
    ├── index.html
    ├── api/feedback.php  线上 PHP 环境的反馈接口
    ├── data/             书目、导航、维度、作者、译文
    └── pic/
        ├── authors/      作者肖像
        └── covers/       封面目录。仓库不附带图片
```

可编辑的底稿是 `public/data/books.json`、`dimensions.json`、`navigation.json`。页面实际读取旁边的同名 `.js`，这样双击 html 也能打开。两份要保持一致。译文在 `public/data/i18n/`，缺一句就回退到简体中文。

## 封面和肖像

出版社书封不进这个仓库。没有封面文件时，卡片显示纸面书名。文件名是书目 id，例如 `public/pic/covers/某id.jpg`。

<https://bk.6-66.cc/> 使用站长本地匹配过的封面，只在该站展示，不作为仓库的一部分再分发。

作者肖像来自 Wikimedia Commons，按各文件原来的许可使用。本仓库没有逐张保存来源页。

## 意见反馈

浏览器打开本地服务时，接口是 `/api/feedback`。放到带 PHP 的网站上时，把 `/api/feedback` 内部转到 `api/feedback.php`。称呼最长 40 字，正文最长 2000 字。服务器记下连接 IP，不采用浏览器自己填的 IP。

## 在线站点

作业和阅读目录的公开地址是 <https://bk.6-66.cc/> 。仓库主页也指向这里。
