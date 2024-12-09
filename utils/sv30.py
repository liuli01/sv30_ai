#%%
import math
def get_scale(x, x1, x10, t):
    x03=x-(1-0.3)/(10-1)*(x10-x1)
    # 修正倾斜角度 t
    t_radians = t * math.pi / 180  # 将角度转换为弧度
    x_adjusted = x / math.cos(t_radians)  # 修正后的高度
    
    # 如果水面高度 x 小于等于 0.3，则返回 0（表示被遮挡）
    if x_adjusted< x03:
        return 0
    # 对修正后的水面高度进行处理：如果在 0.3 到 1 之间，进行线性插值
    if x_adjusted < x1:
        scale = (x_adjusted - x03) / (x1 - x03) * (1 - 0.3) + 0.3
        return scale
    # 对修正后的水面高度进行处理：如果在 1 到 10 之间，进行线性插值
    if x_adjusted < x10:
        scale = (x_adjusted - x1) / (x10 - x1) * (10 - 1) + 1
        return scale
    # 对修正后的水面高度进行处理：如果大于等于 10，则返回 10
    return 10

#%%
def calculate_sv30(predictions,height=1080):
    # 初始化各类物体位置
    sewage_y = None
    point_y = None
    scale_1_y = None
    scale_10_y = None

    # 解析预测结果，获取各类别的 y 坐标
    for pred in predictions:
        if isinstance(pred, dict):
            if pred.get('class') == 'sewage':
                sewage_y = height - (pred['y']- pred['height'] / 2 )
                sewage_y_conf = float(pred['confidence'])
            elif pred.get('class') == 'point':
                point_y = height - (pred['y'] - pred['height'] / 2)  # 获取污泥与水体交界点的最高点
                point_y_conf = float(pred['confidence'])
            elif pred.get('class') == '1':
                scale_1_y = height - (pred['y'] - pred['height'] / 2 )
            elif pred.get('class') == '10':
                scale_10_y = height - (pred['y'] - pred['height'] / 2 )

    # 计算 SV30 读数
    # print(sewage_y,point_y,scale_1_y,scale_10_y)
    if sewage_y is not None and point_y is not None and scale_1_y is not None and scale_10_y is not None:
        max_height = max(sewage_y, point_y)
        value = get_scale(max_height,scale_1_y,scale_10_y,10)
        sv30 = round(value/10, 2)
        conf=round(min(sewage_y_conf,point_y_conf),2)
        return sv30,conf
    elif sewage_y is not None and scale_1_y is not None and scale_10_y is not None:
        value = get_scale(sewage_y,scale_1_y,scale_10_y,10)
        sv30 = round(value/10, 2)
        conf=round(sewage_y_conf,2)
        return sv30,conf
    elif point_y is not None and scale_1_y is not None and scale_10_y is not None:
        value = get_scale(point_y,scale_1_y,scale_10_y,10)
        sv30 = round(value/10, 2)
        conf=1
        return sv30,conf
    else:
        return 0,1


if __name__ == "__main__":
    # 测试数据
    from infer import plot_result

    predictions = plot_result("tests/5.jpg","predict/predict.jpg")["predictions"] # type: ignore
   
    print(predictions)
    # 计算 SV30 读数
    sv30,conf = calculate_sv30(predictions)
    print(f"污泥沉降 SV30 读数: {sv30}, 污泥沉降置信度:{conf}")
    
