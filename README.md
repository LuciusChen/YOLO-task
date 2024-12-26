# 启动

``` shell
python -m venv ~/yolo-task
source ~/yolo-task/bin/activate
pip install -r requirements.txt
python main.py
```
# addTask
## 入参

``` shell
curl -X POST "http://127.0.0.1:8000/add_task/" \
     -H "Content-Type: application/json" \
     -d '{"file_path": "sky/DJI_20241024192552_0002_V.MP4","file_type":"video"}'
```

``` shell
curl -X POST "http://127.0.0.1:8000/add_task/" \
     -H "Content-Type: application/json" \
     -d '{"file_path": "sky/DJI_20241212151628_0004_V.JPG","file_type":"image"}'
```
### 可选参数
1. `"target_classes":[0, 1, 2]`，传入需要特定识别的 classes。classes 对应的 code 参考[coco8](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco8.yaml) 或者由自己训练的数据集中的 `yaml` 定义。
2. `"extra_data":{}`，传入需要的参数，可供回调函数中处理后续逻辑使用。

## 出参

``` json
{
    "task_chain_id": "b746bfa6-438d-4a50-944a-23a7ff443259",
    "code": 200,
    "status": "任务已加入队列"
}
```

# getResult
## 入参

取 `add_task` 中的 `task_chain_id` 查询相关状态。

``` shell
curl -X GET "http://127.0.0.1:8000/get_result/d5d39043-0b72-4a2c-b9be-ed1413fec3ee"
```

## 出参

没有识别到目标时，返回参数。

``` json
{
    "task_id": "d54fedd8-3618-426e-95f6-93399a5730df",
    "code": 204,
    "status": "未识别到任何类，任务链已中止"
}
```

识别到目标时，返回参数。

``` json
{
    "task_id": "c0958bfb-02c2-436c-b8a8-3e1fbb2ec898",
    "code": 200,
    "status": "任务成功",
    "result": {
        "class_counts": {
            "remote": 1
        },
        "oss_key": "output/DJI_20241011093506_0001_V.mp4"
    }
}
```

# GUI 访问

默认是 `http://localhost:5555`
