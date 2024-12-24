# 启动

``` shell
source ~/yolo-task-api/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
celery -A tasks worker --loglevel=info
```
# addTask
入参

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

# getResult

``` shell
curl -X GET "http://127.0.0.1:8000/get_result/d5d39043-0b72-4a2c-b9be-ed1413fec3ee"
```

没有识别到目标时，返回参数。这个时候不会去删除源文件。

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
