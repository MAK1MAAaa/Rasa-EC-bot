---
license: Apache License 2.0
---
数据集文件元信息以及数据文件，请浏览“数据集文件”页面获取。

当前数据集卡片使用的是默认模版，数据集的贡献者未提供更加详细的数据集介绍，但是您可以通过如下GIT Clone命令，或者ModelScope SDK来下载数据集

#### 下载方法 
:modelscope-code[]{type="sdk"}
:modelscope-code[]{type="git"}

本数据集包含了两个字段：

conversations：经过GPT-4o翻译后的对话，可以用于训练一个古文话痨模型
origin：原对话，去掉了最后的user（使assistant在对话中最后出现）
注意conversations和origin的对话长度未必完全一致，有时候GPT-4o会增加一截对话。

对话样例：