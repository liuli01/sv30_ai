#%%
from inference_sdk import InferenceHTTPClient
import supervision as sv
import cv2
# from config import settings
import os
import dotenv
dotenv.load_dotenv()

api_url =str(os.getenv("API_URL"))
api_key = str(os.getenv("API_KEY"))
model_id=str(os.getenv("MODEL_ID"))


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
    print(noplot_result("http://10.9.0.9:8080/ipccamera/img/2024-12-05/camera_1733381322.jpg"))
    print(noplot_result("upload/test.jpg"))
    plot_result("upload/test.jpg","predict/predict.jpg")