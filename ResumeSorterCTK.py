import customtkinter as ctk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
import os
import subprocess
from google.auth import credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import threading
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = 'gogle-llm-api-testing'
REGION = 'us-central1'
JOB_DESCRIPTION = """With more than 218,000 members we’ve been a part of the Tasmanian community for 100 years – we're Tasmania’s shoulder to lean on and voice when it matters. 
Our values guide us in all that we do – Engage with Heart, Unleash Potential, Walk the Talk and Together we Thrive. 
With our local knowledge and as the state’s number one brand we’re here to support our members by helping them enjoy life, 
giving them a helping hand and making their money go further. 

About the role:
As RACT continues to create more value for Tasmanians, we have a fantastic opportunity for someone to join our team in a permanent role as a Data Science & Insights Analyst.
We’re looking for an individual with a curious mind and great problem-solving capabilities. 
This role works across the RACT business and with stakeholders to research, investigate, co-design and build data & analytics business solutions. 
As a member of the Data Science & Insights team, within the Business Intelligence & Analytics Department, you will lean into data science, 
including visualisation and data storytelling, and collaborate with and support colleagues to understand, interpret and make informed decisions. 
You will have the chance to apply business intelligence software, statistical packages and spatial data aligned to a broad range of member and community outcomes.

The successful candidates will have:
A tertiary level grounding or experience in data, analytics, or science (or related field).
The ability to analyse business data, uncover insights and correlations and to present findings and recommendations to 
team leaders or internal stakeholders in a way that is easily understood and actionable.
An affinity and attention to detail when it comes to problem solving related to uncovering valuable insights in both structured and unstructured datasets.
The ability to work independently and meet business outcome deadlines.
Proven experience in fostering new relationships and promoting collaboration.
Exposure to statistical and computational coding languages (i.e. SQL, Python, R).
A desire to support Tasmanian’s and help RACT deliver on our vision.
 
At RACT, we’re not just a workplace – we’re a community. When you join our team, you become part of something bigger. 
Your ideas and the work you do will help shape our community and environment.

Here’s why you’ll love being part of our team:

Flexible work: Life isn’t one size fits all, and neither is our work. Balance your commitments with our flexible work environment.
Career growth: We invest in your development because your success is our success.
Superannuation contribution matching: For every dollar you contribute to your superannuation, we’ll match it up to 2%.
Staff discounts: Enjoy significant discounts on RACT products.
Extra leave: Three extra days on top of annual leave – because self care matters.
Dog-friendly days: You read that right. Bring your furry friend to the office – tail wags guaranteed!
Volunteer opportunities: Make a difference beyond the office walls.
"""

# Store uploaded PDFs and their grades
pdf_data = {}

def update_table_display():
    # Updates the display table with the current PDF data and grades.
    global table_display
    table_display.configure(state="normal")
    #deletes whole text box
    table_display.delete("1.0", "end") 

    #Create new text box
    header = f"{'Filename':<40} {'Grade (Out of 5)':<10}\n"
    table_display.insert("1.0", header)
    table_display.insert("end", "-" * 50 + "\n")
    
    #add all the files
    for filename, data in pdf_data.items():
        grade = data.get('grade', 'Pending')
        line = f"{filename:<40} {grade:<10}\n"
        table_display.insert("end", line)

    table_display.configure(state="disabled")


def upload_file():
    # Handles the file upload process for PDF files, extracts text, and updates the display table.
    filename = filedialog.askopenfilename(title="Select a file", filetypes=[("PDF files", "*.pdf")]) #should only show pdf's
    if filename:
        try:
            #check if it's already been uploaded
            pdf_name = os.path.basename(filename)
            if pdf_name in pdf_data:
                messagebox.showwarning("Warning", "This file has already been uploaded!")
                return

            # Open the PDF with PyMuPDF
            pdf_document = fitz.open(filename)
            text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                text += page.get_text()

            # Store PDF data
            pdf_data[pdf_name] = {
                'path': filename,
                'text': text,
                'grade': 'Pending'
            }
            
            update_table_display()
            output_label.configure(text=f"Successfully uploaded: {pdf_name} \n Preview: {text[:200]}")

            print(repr(text))

        except Exception as e:  # Handle potential errors (e.g., file not found)
            messagebox.showerror("Error", f"Error reading file: {e}")

def show_countdown_message(countdown_event):
    # Sends the resume text to the Gemini model for grading, with optional exponential backoff.
    dialog = ctk.CTkToplevel()
    dialog.title("Countdown")
    dialog.geometry("200x100")
    
    label = ctk.CTkLabel(dialog, text="Countdown: 10")
    label.pack(pady=20)

    def countdown(n):
        if n > 0:
            label.configure(text=f"Countdown: {n}")
            dialog.after(1000, countdown, n - 1)  # Schedule next countdown
        else:
            countdown_event.set()  # Signal that countdown is complete
            dialog.destroy()  # Close the dialog when done

    countdown(10)  # Start countdown from 10

def send_to_gemini(text, exp_back_off):
    # This takes the text from a resume and gets gradeing from gemini and also might implement exponential back off

    #jank non-exponential back off that was not promised in the description.
    if exp_back_off:
        # Show countdown dialog
        countdown_event = threading.Event()
        show_countdown_message(countdown_event)  # Show the countdown message
        countdown_event.wait()



    try:
        prompt = (
            "Please grade the following text from a resume based on how suitable the candidate is for the job. The text is taken from a pdf, ignore all \ escapes such as \\n etc"
            "Only give a 1 to 5 rating, expressed as a single interger, do no put any other characters or number in the response, it should be only one number. "
            "1 should be for poeple who have little to no experience or qualifications listed on the job description"
            "2 is for poeple with either weakly matching the qualifications or a limited experince in the field in related fields"
            "3 is for those who match some of the qualifications but may have skills in other in related fields"
            "4 is for those who match most of the qualifications necessary and have other skill that may be useful"
            "5 is reserved those who match 80% of the qualifications required for the job and who sometimes have extra skills in the field."
            f"\n The job description is: {JOB_DESCRIPTION}" 
            f"\n The text from the resume is: {text}"
        )
        model = GenerativeModel("gemini-1.5-flash-002")
        response = model.generate_content(prompt) #response validity is checked in the while loop in assign_grades()

        return response.text
    except Exception as e:
        if "quota exceeded" in str(e).lower():
            return "quota exceeded"
        return "Exception thrown: {str(e)}"
        


def assign_grades():
    # Iterate over 'pdf_data'
    # For each PDF, call 'send_to_gemini()' to get the grade
    # Update the "grade" field for the PDF
    # Update UI with graded results
    
    for pdf_name in pdf_data:
        exp_back_off = False
        max_attempts = 0
        while pdf_data[pdf_name]['grade'] not in '12345' and max_attempts < 3:
            
            max_attempts += 1
            grade = send_to_gemini(pdf_data[pdf_name]['text'], exp_back_off)
            grade = grade.strip()
            
            #delete later
            print(len(grade) == 1)
            print(f"grade len: {len(grade)}")
            print(grade in '12345')
            for char in grade:
                print(f"Character '{char}' has ASCII value: {ord(char)}")

            if len(grade) == 1 and grade in '12345':
                pdf_data[pdf_name]['grade'] = grade
                print('grading success')
                break
            
            print('did not grade')
            if grade == "quota exceeded":
                print("quota exceeded")
                messagebox.showerror("Quota exceeded", "Your gemini query quota has been exceeded, please wait 1 minute and try again by clicking \"Grade Resumes\". ~3 requests per minute allowed.")
                return
                exp_back_off = True
            print(grade)
        
        print("running update_table_display()")
        update_table_display()




def init_vertexai():
    vertexai.init(project=PROJECT_ID, location=REGION)
        

def clear_data():
    # Clears all uploaded PDF data and updates the display table accordingly.
    if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all data?"):
        pdf_data.clear()
        update_table_display()
        output_label.configure(text="All data cleared")


def authenticate_gcloud():
    #not implemented
    return


    #Both are these are flags for cancellation of the function
    finished = threading.Event()

    def return_true():
        finished.set()
        #messagebox.destroy()
        return True
    
    def return_false():
        finished.set()
        #messagebox.destroy()
        return False
    '''
    def show_message():
        if not messagebox.askquestion("Authentication in progress", "Authentication in progress, would you like to cancel?"):
            finished.set()
            return False
        else:
            finished.wait()
    '''

    def show_message():
        dialog = ctk.CTkToplevel()
        dialog.title("Authentication")
        dialog.geometry("300x100")
        
        label = ctk.CTkLabel(dialog, text="Authentication in progress\nWould you like to cancel?")
        label.pack(pady=10)
        
        def on_cancel():
            finished.set()
            dialog.destroy()
        
        cancel_button = ctk.CTkButton(dialog, text="Cancel", command=on_cancel)
        cancel_button.pack(pady=5)
        
        # Wait for authentication to complete
        finished.wait()
        dialog.destroy()  # Close window when auth is done




    message_thread = threading.Thread(target=show_message)
    message_thread.start()


    try:
        gcloud_path = r"C:\Users\aaron\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        result = subprocess.run(
            [gcloud_path, "auth", "list"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if "No credentialed accounts." in result.stdout:
            print("No authenticated accounts found")
        else:
            print("Already authenticated")
            print(result.stdout)
            return_true()
            
    except subprocess.CalledProcessError as e:
        print(f"Error checking authentication: {e}")
        print("Error Output:", e.stderr)
        return_false()
    

    try:
        gcloud_path = r"C:\Users\aaron\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        # Run the gcloud command and capture the output
        result = subprocess.run(
            [gcloud_path, "auth", "application-default", "login"],
            check=True,         # Raise an exception for non-zero return codes
            text=True,          # Capture the output as a string (not bytes)
            stdout=subprocess.PIPE,  # Capture standard output
            stderr=subprocess.PIPE   # Capture standard error
        )
        
        if "Credentials saved to file" in result.stdout:
            print("Authentication successful.")
            print("Output:", result.stdout)   # Print standard output
            print("Errors:", result.stderr)   # Print any error messages
            return_true()
        else:
            return_false()


    except subprocess.CalledProcessError as e:
        print(f"Error during authentication: {e}")
        print("Error Output:", e.stderr)  # Print detailed error output if available
        return_false()


def main():
    
    # Initialize customtkinter
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk() 
    root.title("Resume Grader")
    root.geometry("700x500")  # Made window taller for table

    label = ctk.CTkLabel(master=root, text="Upload resumes and then click 'Grade Resumes'", font=('roboto', 24))
    label.pack(padx=10, pady=10)

    # Create a frame for buttons
    button_frame = ctk.CTkFrame(master=root)
    button_frame.pack(pady=10)

    # Place buttons side by side in the frame
    upload_button = ctk.CTkButton(master=button_frame, text="Upload File", command=upload_file)
    upload_button.pack(side="left", padx=5, pady=5)

    grade_button = ctk.CTkButton(master=button_frame, text="Grade Resumes", command=assign_grades)
    grade_button.pack(side="left", padx=5, pady=5)

    clear_button = ctk.CTkButton(master=button_frame, text="Clear Data", command=clear_data)
    clear_button.pack(side="left", padx=5, pady=5)

    auth_button = ctk.CTkButton(master=button_frame, text="Authenticate GCloud", command=authenticate_gcloud)
    auth_button.pack(side="left", padx=5, pady=5)

    init_vertex = ctk.CTkButton(master=button_frame, text="Initialize VertexAI", command=init_vertexai)
    init_vertex.pack(side="left", padx=5, pady=5)

    # Add table display
    global table_display
    table_display = ctk.CTkTextbox(master=root, width=500, height=200, state = "disabled")
    table_display.pack(padx=20, pady=10, fill="both", expand=True)
    update_table_display()  # Initialize empty table
    
    global output_label
    output_label = ctk.CTkLabel(master=root, text="")
    output_label.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
