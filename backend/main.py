from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Union
from PIL import Image
import io
import base64
import openai
import os
import requests
import json
from exa_py import Exa
from typing import List, Dict 
import re
from dotenv import load_dotenv
load_dotenv()




# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
exa = Exa(api_key="")


app = FastAPI(title="DAPARTO Assistant", description="DAPARTO Customer Assistant", version="0.1")

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to encode the image
def encode_image(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')

prompt_for_vin = """

Identify in the image the VIN number and return it in the JSON format: 
{ 
   "status": "success",
   "overview": 'overview of vehicle identified', 
   "make": 'make of vehicle', 
   "model": 'model of the vehicle, 
   "model_year":'model year of the vehicle', 
   "engine": 'engine of the vehicle', 
   "assembly_plant": 'assembly plan of the vehicle', 
   "serial_number": 'serial number of the vehicle', 
... any other keys you may identify in the same key value pairs ...
}. 

If no product is present, please return 
{
   "status" : "error",
   "message" : "Vin is not correctly identified and may be wrong.. add any other information"
}

"""

@app.post("/daparato-assistant/")
async def daparato_assistant(
    file: Optional[Union[UploadFile, str]] = File(None),
    search_string: Optional[str] = Form(None),
    previous_messages: Optional[str] = Form(None),
):
    if not file and not search_string:
        raise HTTPException(status_code=400, detail="You must provide either an image or a search string.")

    # Initialize the combined search input
    combined_search_input = ""
    vin_information = None
    # If image is provided, process the image
    if file and file.filename:
        try:
            if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
                raise HTTPException(status_code=400, detail="Invalid file type. Only PNG and JPEG images are supported.")

            print("Loading image:", file.filename)
            image = Image.open(io.BytesIO(await file.read()))

            # Encode the image to base64
            base64_image = encode_image(image)

            # Prepare the payload for OpenAI API
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_for_vin},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ]
            }

            # Make the request to OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai.api_key}",
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

            # Handle the response
            if response.status_code == 200:
                result = response.json().get("choices")[0].get("message").get("content")
                print("OpenAI API Response:", result)
                
                # Parse the result to remove any surrounding ```json and ```
                result_dict = eval(result.strip("```json").strip("```").strip())

                # Check if the VIN was correctly identified
                if result_dict.get("status") == "error":
                    print("Error identifying VIN:", result_dict.get("message"))
                else:
                    print("VIN identified:", result_dict)
                    vin_information = result_dict
                    # Add the identified vehicle information to the combined search input
                    combined_search_input += f"Vehicle overview: {result_dict.get('overview')} Vehicle Make: {result_dict.get('make')} Vehicle Model: {result_dict.get('model')}"

            else:
                print("Error from OpenAI API:", response.status_code, response.text)
                return JSONResponse(content={"error": response.text}, status_code=response.status_code)

        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=400)

    # If query is provided, add it to the combined search input
    if search_string:
        get_intent_response = await get_intent(search_string, vin_information)
        if combined_search_input:
            # Combine the search strings if both image and text are provided
            combined_search_input += f" AND {get_intent_response}"
        else:
            # Use only the search string if no image was processed
            combined_search_input = get_intent_response

    # get answers to the user query
    get_answer = await assistant_answer(search_string, previous_messages)

    # given the intent, suggest questions to ask the user
    suggested_questions = await suggest_questions(combined_search_input, previous_messages)
    return { 
        "assistant_answer": get_answer, 
        "intent": get_intent_response, 
        "suggested_questions": suggested_questions
        }

    

intent_prompt = """
Given the user query, and the provided vin as context, convert to json with user's intent in a structured way as specified. 
Do not add any additional information as the user query json will be used to run the search query.


Return it as following json. Only use the keys provided below. 
{
  "intent": <intent e.g. searching_for_a_part, looking_for_order, looking_for_guidance>,
  "query": <actual user query>,
  "vin_information": <complete vin information if provided>,
  "expanded_query": <expand and clarify user query if needed ie if user query is ambiguous>
}

example output

 "part_number": "D1060-SL0-A02",
  "vehicle": {
    "make": "Acura",
    "model": "TL",
    "model_year": "1994",
    "engine": "3.2L V6",
    "assembly_plant": "Marysville, Ohio, USA",
    "vin": "JH4NA1"
  }


"""
async def get_intent(query: str, vin_information : Optional[Dict]):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        response_format= { "type": "json_object"},
        messages=[
            {
                "role": "system", "content": intent_prompt,
                "role": "user", "content": f"User query: {query}. Provided vin information as context: {vin_information} \n Return as JSON object."
            }
        ]
    )
    print("Intent response:", response.choices[0].message.content)
    intent = response.choices[0].message.content

    return intent

suggest_questions_prompt = """

You are DAPARTO Assistant. You are helping me (the user) find the right part for my vehicle or diagnose an issue.

Based on my query {query} and our previous conversation {Previous conversation}, use the following guidelines to suggest maximum 4 questions. The questions should always be written in the first person, guiding me step-by-step. 

If no query is provided, start with a basic question (in the first person) about my vehicle information or ask for my VIN.

Example questions in the first person:
- I am looking for a part for my vehicle.
- I am experiencing an issue with my car.
- I need help identifying a part for my car.

### Guidelines for Questions:

1. **Vehicle Information:**
   - **Make (e.g., Volkswagen):**
     - "I need to provide the make of my vehicle. Is it a Volkswagen, Toyota, Ford, etc.?"

   - **Model (e.g., Jetta):**
     - "I should provide the model of my vehicle. If I’m not sure, I can find it on the back of my car or on the registration papers."

   - **Year (e.g., 2015-2017):**
     - "I need to know the year of manufacture of my vehicle. I can find this information on my car's registration or insurance document."

   - **Trim Level (e.g., SE, SEL, TDI):**
     - "I need to provide the trim level of my car. It might be listed on the side of my car, like SE, SEL, or TDI. If I’m unsure, I can provide the VIN."

   - **Engine Type (e.g., 1.4L TSI, 2.0L TDI):**
     - "I should know the engine type or size of my vehicle. For example, it could be 1.4L TSI or 2.0L TDI. If I don’t know, it might be listed in the owner’s manual or on a label under the hood."

2. **VIN (Vehicle Identification Number):**
   - **Encouraging Question:**
     - "The VIN is a 17-character code unique to my vehicle and helps find the exact part match. I should provide it. It can be found on the driver's side dashboard or on my vehicle's registration document."

   - **Guidance If Uncertain:**
     - "If I’m not sure where to find the VIN, it’s usually on a small metal plate visible from the windshield on the driver’s side or on a sticker inside the driver's door frame."

3. **Part Description:**
   - **General Part Type:**
     - "I need to specify which part of the vehicle the item is for. Is it for the engine, suspension, brakes, or something else?"

   - **Location on Vehicle:**
     - "I should describe where this part is located on my car. For example, is it under the hood, near the wheels, or inside the car?"

   - **Specific Usage or Function:**
     - "I should describe what this part does. Is it an electrical component like a sensor, a mechanical part like a belt, or something else?"

4. **Specific Symptoms or Issues:**
   - **Issue Clarification:**
     - "I need to explain what issue I am experiencing with my car that leads me to think I need this part. For example, is there a noise, a warning light, or is something not working?"

   - **Condition of the Current Part:**
     - "I need to specify if the current part is broken, worn out, or missing. Or am I looking to upgrade or replace it with a different type?"

5. **Existing Part Number:**
   - **Checking for Existing Parts:**
     - "I need to check if I have the old part with me, or if I know its part number. This can make finding the correct replacement much easier."

   - **Alternative if No Part Number:**
     - "If I don’t have the part number, I should describe any markings or labels on the part. A photo can also be very helpful."

### Output Format:

Return the output as a JSON object as follows. Each question should be in the first person, with relevant options included. Options should be auto-filled free text fields, and where appropriate, include "File Upload" options for uploading images.
Return 4 questions at maximum.


{
  "suggested_questions": [
    {
       "question_text": "<related question to original query 1>",
       "question_options": ["<option 1>", "<option 2>", "<option 3>", "free text"]
    },
    {
       "question_text": "<related question to original query 1>",
       "question_options": ["<option 1>", "<option 2>", "<option 3>", "free text"]
    },
  ]
}

example output

{
  "suggested_questions": [
    {
      "question_text": "I am looking for a part for my vehicle.",
      "question_options": [{"VIN_number": "free text", "VIN_image": "File Upload", "Free_text": "free text"}]
    },
    {
      "question_text": "Help me diagnose a problem with my car.",
      "question_options": [{"VIN_number": "free text", "VIN_image": "File Upload", "Free_text": "free text"}]
    }
  ]
}


"""
@app.post("/suggest-questions/")
async def suggest_questions(query: Optional[List[Dict]], previous_messages: Optional[List[Dict]]):
    response = openai.chat.completions.create(
        model="gpt-4o",
        response_format= { "type": "json_object"},
        messages=[
            {
                "role": "system", "content": suggest_questions_prompt,
            },
            # Only add the user message if query is not None
             *(
                [{
                    "role": "user",
                    "content": f"Original user query: {query}. \n Previous conversation: {previous_messages} \n Suggest questions as JSON object, as specified."
                }] if query else []
            )
        ]
    )
    print("Suggested questions:", response.choices[0].message.content)
    intent = response.choices[0].message.content

    return intent

answer_prompt = """

You are DAPARTO Assistant. You are helping me (the user) find the right part for his vehicle or diagnose an issue.
Given the user query and previous messages, provide an answer to the user query.

For part numbers or provide the url to the part number in the format: 
https://www.daparto.de/Teilenummernsuche/Teile/Alle-Hersteller/{part_number}?ref=fulltext

Replace the {part_number} with the actual part number.

In your answer be detailed and mention all information you have from user and you used to get to the answer. 

"""
@app.post("/find-answer/")
async def assistant_answer(query: Optional[List[Dict]], previous_messages: Optional[List[Dict]]):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", "content": answer_prompt,
            },
            {
                "role": "user",
                "content": f"User query: {query}. Previous conversation: {previous_messages}. "
            }
        ]
    )
    print("Answer from assistant:", response.choices[0].message.content)
    answer = response.choices[0].message.content

    return answer


@app.get("/")
async def read_main():
    return {"message": "Welcome to DAAPARTO Assistant!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)