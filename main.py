import base64
import os
import tempfile
import fitz
import sys
import jinja2
from pathlib import Path
import shutil
import json

sbc_prompt = """
    Parse the benefits in the image. Return a JSON array of all services I can access (like Urgent Care, Diagnostic test). 
    For each service, define the in network and out of network payment, and format it as {"value": string, "type": "copay" | "coinsurance" | "noCharge" | "notCovered"}. 
    Consider this to called of type payment. Only output valid JSON. Do not include any symbols in the value field, and only use whole numbers.
    Format each deductible and moop as a single whole number. 
    The final output should look like {"carrierName: "", "phone": "", "startDate": "", "endDate": "", familyDeductible: "", indivDeductible: "", familyMoop: "", indivMoop: "", "services": [{"serviceName": string, "in_network": payment, "out_of_network": payment]}.
    The StartDate and EndDate are sometimes referred to as the 'coverage period.' Output them as MM/DD/YYYY.
    Only return JSON. Do not return anything else.
    """

sbc_prompt_2 = """
    What benefits are covered by the plan?
    """

from openai import OpenAI
client = OpenAI()

#convert pdf into array of pngs
def pdf_to_pngs(pdf_path, temp_folder):
    doc = fitz.open(pdf_path)

    #create containing temp folder if doesn't exist
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    # Iterate through the pages of the PDF
    for i, page in enumerate(doc):
        # Render the page as a PNG image
        pix = page.get_pixmap()

        # Save the PNG image
        png_path = f"page_{i+1}.jpg"
        #save to temp folder
        pix.save(temp_folder + "/" + png_path)

    doc.close()

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def png_to_json_vision(temp_folder):
    #crunch it down
    #TODO: need to use jpeg
    fileData = []
    for file in os.listdir(temp_folder):
        if file.endswith(".jpg"):
            png_path = temp_folder + "/" + file
            fileData.append(encode_image(png_path))

    #now make a nice jsonydoo
    content = []
    content.append({"type": "text", "text": sbc_prompt})

    for fd in fileData:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{fd}", "detail": "low"} })

    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
        {
        "role": "system",
        "content": "You are a helpful assistant. Your response should be in JSON format.",
        },
        {
            "role": "user",
            "content": content
        }],
        max_tokens=1600,
    )

    if len(response.choices) == 0:
        return ""

    final_json = response.choices[0].message.content

    #it always wants to do this now
    return final_json.split("```json")[1].split("```")[0]

if __name__ == '__main__':
    if(len(sys.argv) < 3):
        print("Usage: python3 main.py <pdf_path> <plan_name> <site_dir>")
        sys.exit(1)
    
   
    pdf_path = sys.argv[1]
    plan_name = sys.argv[2]
    site_dir_name = sys.argv[3]

    if plan_name == "" or pdf_path == "" or site_dir_name == "":
        print("Usage: python3 main.py <pdf_path> <plan_name> <site_dir>")
        sys.exit(1)

    print("Converting SBC")

    #convert pdf to pngs, and convert those to a single CSV slug
    with tempfile.TemporaryDirectory() as tmpdirname:
        pdf_to_pngs(pdf_path, tmpdirname)
        #csvs = pngs_to_csvs(tmpdirname)

        jsonResult = png_to_json_vision(tmpdirname)

    print("Generating site")

    #make site dir if it doesn't exist
    site_dir = Path(site_dir_name)
    site_dir.mkdir(parents=True, exist_ok=True)

    #save off thee jason
    data_dir = Path(site_dir, "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    new_file = Path(data_dir, "data.json")
    new_file.write_text(jsonResult)

    #relocate thee old plan file
    shutil.copy(pdf_path, data_dir)

    #now, generate website...
    try:
        json_object = json.loads(jsonResult)
    except:
        print("Could not generate parsable data from file. Try again?")
        sys.exit(1)

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = environment.get_template("planTemplate.html")
    result = template.render(plan_name=plan_name, data=json_object)

    site_path = Path(site_dir, "index.html")
    site_path.write_text(result)


    print("Loaded successfully")

    
