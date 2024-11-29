#%%
from inference_sdk import InferenceHTTPClient
import supervision as sv
import cv2
from config import Settings

settings = Settings()
api_url = settings.API_URL
api_key = settings.API_KEY
model_id=settings.MODEL_ID

client = InferenceHTTPClient(api_url,api_key) 
def noplot_result(input_image):
    with client.use_model(model_id=model_id):
        results = client.infer(input_image)
    return results

def plot_result(input_image,output_image):
    results = noplot_result(input_image)
    if len(results['predictions'])>0: # type: ignore
        ## 画出图
        image = cv2.imread(input_image)
        # load the results into the supervision Detections api
        detections = sv.Detections.from_inference(results)
        # create supervision annotators
        bounding_box_annotator = sv.BoundingBoxAnnotator()
        label_annotator = sv.LabelAnnotator()

        # annotate the image with our inference results
        annotated_image = bounding_box_annotator.annotate(
            scene=image, detections=detections)
        annotated_image = label_annotator.annotate(
        scene=annotated_image, detections=detections)

        # display the image
        sv.plot_image(annotated_image)
        # save the image
        cv2.imwrite(output_image, annotated_image)
        return results
    else:
        return None

if __name__ == "__main__":
    print(noplot_result("https://www.helloimg.com/i/2024/11/28/6747e1920dbf7.jpg"))
    # print(noplot_result("test.jpg"))
    # plot_result("test.jpg","predict.jpg")