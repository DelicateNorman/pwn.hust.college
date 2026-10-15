# 平台 REST API (REST API)

平台的全部做题流程都可以通过 REST API 完成:查询题目、启动题目容器、SSH 连接、提交 flag,无需浏览器。网页前端调用的就是这些接口,因此结果与网页操作完全一致。本文档面向需要在命令行环境下使用平台的学生、脚本与 Agent 工具开发者。

## 认证

先在网页上生成 API Token:登录后进入 **设置 → 访问令牌**,创建一枚 Token。之后在每个请求中携带两个请求头:

```text
Authorization: Token <你的Token>
Content-Type: application/json
```

**两个请求头缺一不可,包括没有请求体的 GET 请求**。缺少 `Content-Type: application/json` 时,Token 不会被识别,请求会被当作未登录处理。

请妥善保管 Token,不要写入脚本、日志或提交到代码仓库。

## 接口一览

| 用途 | 方法与路径 | 说明 |
|---|---|---|
| 验证 Token | `GET /api/v1/users/me` | 返回当前用户信息 |
| 已解题目列表 | `GET /api/v1/users/me/solves` | 选题前先过滤已完成的题目 |
| 题目列表 | `GET /pwncollege_api/v1/dojo/<道馆>/<模块>/challenges` | 返回 `{"success": true, "challenges": [...]}`,注意列表在顶层 `challenges` 键下;每题含字符串 `id`(开题用)和数字 `challenge_id`(提交用)及题面 |
| 启动题目 | `POST /pwncollege_api/v1/docker` | 请求体 `{"dojo": "...", "module": "...", "challenge": "..."}`,参数用字符串 `id` |
| 查询当前题目 | `GET /pwncollege_api/v1/docker` | 返回当前运行中的道馆/模块/题目 |
| 上传 SSH 公钥 | `POST /pwncollege_api/v1/ssh_key` | 请求体 `{"ssh_key": "<公钥>"}` |
| 删除 SSH 公钥 | `DELETE /pwncollege_api/v1/ssh_key` | 请求体 `{"ssh_key": "<存储值>"}`,存储值不含注释(见下文"公钥管理") |
| 提交 flag | `POST /api/v1/challenges/attempt` | 请求体 `{"challenge_id": <数字>, "submission": "<flag>"}` |

## 命令行做题完整流程

以下示例假设 Token 保存在环境变量 `TOKEN` 中。

```bash
# 1. 查看某道馆某模块的题目(以 welcome 道馆 welcome 模块为例)
curl -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     https://pwn.cse.hust.edu.cn/pwncollege_api/v1/dojo/welcome/welcome/challenges

# 2. 启动题目(其中的 id 来自上一步的返回值)
curl -X POST -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     -d '{"dojo":"welcome","module":"welcome","challenge":"flag"}' \
     https://pwn.cse.hust.edu.cn/pwncollege_api/v1/docker

# 3. 等待约 20 秒后 SSH 连接(容器需要初始化时间)
ssh -tt -i ~/.ssh/key -o StrictHostKeyChecking=no \
    hacker@pwn.cse.hust.edu.cn

# 4. 在容器内阅读题面并完成题目
cat /challenge/DESCRIPTION.md

# 5. 提交 flag(challenge_id 是题目列表里的数字编号)
curl -X POST -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     -d '{"challenge_id":73,"submission":"pwn.college{...}"}' \
     https://pwn.cse.hust.edu.cn/api/v1/challenges/attempt
```

提交成功时返回 `data.status` 为 `correct`;返回 `already_solved` 表示该题此前已完成,同样视为成功。

## 注意事项

### 容器行为

- 每个用户同一时间只有一个题目容器,启动新题目会自动销毁旧容器;`/home/hacker` 目录在题目之间持久保留。
- 启动接口约一秒内返回成功,但容器初始化需要约 20 秒,之后 SSH 才能连接。连接失败时稍等重试即可。
- 容器闲置约 6 小时后自动销毁。

### SSH 连接

- 建议始终使用 `ssh -tt` 强制分配终端:部分题目会校验 `SSH_TTY` 环境变量,无终端时会拒绝运行。
- 题目验证程序的路径以 `/challenge/DESCRIPTION.md` 的说明为准,常见为 `/challenge/solve`,部分道馆(如 git)为 `/challenge/check`。

### 公钥管理

- 平台每个账号只保存**一把** SSH 公钥。上传新公钥时如果返回 `"SSH Key already in use"`,含义是账号已有公钥(而不是这把钥匙被别人占用),需要先删除旧的再上传。
- 上传时平台会去掉公钥行尾的注释部分,因此删除时也要传入不含注释的值,即公钥行 `cut -d' ' -f1,2` 的结果。
- 公钥也可以在网页 **设置 → SSH 公钥** 中查看和删除;更换公钥前建议先记录原值,用完恢复。删除旧公钥到上传新公钥之间,SSH 访问会短暂中断。

### 道馆与题目发现

- `GET /pwncollege_api/v1/dojo/<道馆>/modules` 接口当前返回 500,模块列表请从道馆页面(如 `https://pwn.cse.hust.edu.cn/welcome/`)的链接中获取;全部道馆可从 `https://pwn.cse.hust.edu.cn/dojos` 页面发现。
- 部分道馆有前置道馆要求,其页面不显示模块链接并会提示前置道馆,需先完成前置道馆。
- 过滤已完成题目时,请以 `solves` 接口返回的数字 `challenge_id` 为准并实时查询:题目可能随模块调整而重新组织,历史清单会过期。

### flag 格式

flag 为 `pwn.college{...}` 形式的字符串,不含空白字符,可直接放入 JSON 提交。

## 参考实现

[hust-open-atom-club/pwnhustcollege_skill](https://github.com/hust-open-atom-club/pwnhustcollege_skill) 提供了封装上述全部接口的辅助脚本(`scripts/platform_api.sh`)与面向 Agent 的完整做题流程说明,可作为脚本开发或 Agent 接入的起点。
