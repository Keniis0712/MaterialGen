## MaterialGen
一个用于从新闻中自动生成作文素材的工具

### 特点
- 具有Web界面，可以方便从网页查看、使用、管理等
- 全自动化，无需人工干预

### 部署
使用Python3.12+版本，一键安装依赖
```commandline
pip install -r requirements.txt
```
在`run.sh`或`run.bat`中配置API_KEY，按照需求配置监听地址与端口，直接运行即可。
第一次启动时会自动创建管理员账号，用户名:admin，密码:THEPassword，登录Web控制界面后可修改密码
