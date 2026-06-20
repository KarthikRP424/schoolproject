# AI School Issue Monitoring and Priority Agent

A beginner-friendly, offline decision support system for government school monitoring. This project demonstrates how rule-based AI agents can solve critical administrative challenges in public education without requiring paid APIs or internet access.

---

## 1. Project Overview
The **AI School Issue Monitoring and Priority Agent** is a Streamlit-based web application that acts as an intelligent router and decision support assistant. It accepts report logs of school issues submitted by headmasters, village volunteers, student representatives, or education officers. It classifies the category, assigns a priority score (0–100) and urgency level, assesses risk/credibility, and outputs an actionable next step alongside a copy-paste-ready officer brief.

---

## 2. Problem Statement
In large government school networks (such as those in Karnataka), departments receive thousands of complaints ranging from minor furniture issues to critical safety hazards. 
* **The Bottle-Neck:** Manually sorting, classifying, and prioritizing these reports is slow, leading to delayed action on dangerous hazards.
* **Connectivity Hurdles:** Many rural blocks have unstable internet, making heavy cloud-based AI solutions (like OpenAI or Anthropic APIs) expensive, slow, and unreliable.
* **Decision Fatigue:** Education officers need structured summaries and clear action guidelines rather than raw, unstructured feedback to make fast decisions.

---

## 3. Why This Project Belongs to "Agents for Good"
This project falls directly under the **Agents for Good** track because it:
* **Promotes Educational Equity:** By accelerating repairs of toilets, water supplies, and structures, it ensures students (especially girls) remain in school in a safe environment.
* **Is Accessible to Underserved Areas:** By running 100% offline, it allows low-budget local administrations to utilize decision support technology without software licensing costs.
* **Empowers Local Voices:** It provides students, volunteers, and teachers a direct pathway to get issues noticed based on objective severity rules rather than bureaucratic connections.

---

## 4. Agent Workflow
The agent performs its analysis sequentially:
1. **Input Ingestion:** Accepts school name, district, taluk, reporter role, raw description, and evidence checks (photo upload / GPS coordinates).
2. **Category Classification:** Scans for keywords in the description to sort reports into *Sanitation*, *Drinking Water*, *Teacher Shortage*, *Infrastructure*, *Electricity*, or *General Issue*.
3. **Scoring Engine:** Calculates a priority score starting from a baseline of 40, applying weighted adjustments based on category severity, urgency phrases, reporter credibility, and evidence.
4. **Credibility Audit:** Cross-references description length and evidence checkboxes to flag high, medium, or low fake/duplicate risks.
5. **Action Generation:** Maps the final category and priority level to an official next step.
6. **Brief Generation:** Assembles a structured, copy-paste-ready report summarizing the entire case.

---

## 5. Automatic Report Flow
This prototype features a live, session-based workflow connecting school reporters directly to administration officials:
* **Submission:** Headmasters, Student Representatives, and Village Volunteers submit reports.
* **Local Processing:** The report description is run locally through the AI agent to assign categories, scores, urgency flags, and recommended action steps.
* **Database Appending:** The analyzed report, containing its unique ID (e.g., `RPT-0001`) and submission time, is stored directly into the shared `st.session_state["reports"]` list.
* **Officer Dashboard:** Government Officers logging in will immediately see new reports under their jurisdiction. 
* **Alerts & Updates:** Officers see automatic **Urgent Alerts** (reports with Urgent priority) and **Dangerous School Alerts** (schools flagged with hazardous problems), and they can update report status (e.g., from *Pending* to *Under Review* or *Resolved*), which updates the system state dynamically.
* **Session Storage:** All submissions and status updates persist during the current Streamlit session. They reset to defaults when the server restarts.

---

## 6. Demo Login Credentials

This prototype is equipped with pre-loaded demo users representing different administrative roles and access levels.

| Role | Username | Password | School / Jurisdiction |
|------|----------|----------|---------------------|
| **Headmaster** | `headmaster_rampura` | `Head@123` | GHPS Rampura (Bhadravathi Taluk, Shivamogga) |
| **Headmaster** | `headmaster_sagar` | `Head@456` | GHS Sagar (Sagar Taluk, Shivamogga) |
| **Student Rep** | `student_rampura` | `Stu@123` | GHPS Rampura (Bhadravathi Taluk, Shivamogga) |
| **Student Rep** | `student_sagar` | `Stu@456` | GHS Sagar (Sagar Taluk, Shivamogga) |
| **Village Volunteer** | `volunteer_rampura` | `Vol@123` | GHPS Rampura (Bhadravathi Taluk, Shivamogga) |
| **Village Volunteer** | `volunteer_sagar` | `Vol@456` | GHS Sagar (Sagar Taluk, Sagar) |
| **Govt Officer** | `officer_shivamogga` | `Off@123` | Shivamogga District reports only |
| **Govt Officer** | `officer_state` | `State@123` | All District reports (State-wide view) |

---

## 7. Password Reset Feature
* **Reset Interface:** Users can check the **"Forgot / Reset Password"** checkbox on the login page to open the reset form.
* **Rules:** The username must exist in the database, passwords must match, and the new password must be at least **6 characters** long.
* **Scope:** Because this is a lightweight web prototype, password changes are **session-based**. They are temporarily saved in `st.session_state` and will reset back to default when the Streamlit server restarts.
* **Security:** No external databases, email servers, or API keys are required.

---

## 8. Features
* **Interactive Submission Form:** Auto-fills school profiles (name, district, taluk, village) from the reporter's user profile, allowing user edits.
* **Evidence Upload Support:** Live file uploading for photo evidence and coordinate tracking for GPS verification.
* **Officer Portal:** Access-controlled reports log table with total and priority metrics summary charts.
* **Live AI Assessment:** Immediate generation of priority level, score, risk, and action steps.
* **One-Click Download:** Allows officers to download the generated text summary directly to their local computers.

---

## 9. No API Key Design
* **100% Local Logic:** This project does not use any external API keys, paid models, LLM APIs, or secret credentials.
* **Privacy & Cost:** Safe from credit depletion, rate limits, or network timeouts.
* **Reproducibility:** It is fully reproducible locally, in a Kaggle Notebook, or inside a simple sandboxed environment.

---

## 10. Tech Stack
* **Python:** Core programming language.
* **Streamlit:** Fast, lightweight framework for building web interfaces.
* **Pandas:** Used for loading, parsing, and rendering the pre-loaded CSV dataset.

---

## 11. How to Run

### Step 1: Install Python
Ensure Python 3.9+ is installed on your computer.

### Step 2: Install Dependencies
Open your terminal or command prompt in the project directory and run:
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Application
Run the following command to start the local web server:
```bash
streamlit run app.py
```

---

## 12. How to Share the App

> [!WARNING]
> **Important sharing note:** By default, running Streamlit using `localhost` works only on your own computer. Other users cannot open `localhost` from their own mobile phones, tablets, or separate laptops.

To share your app with others, use one of the two methods below:

### Method A: Share on the Same Wi-Fi Network
If you and your classmates or colleagues are connected to the same Wi-Fi network:
1. Run this command in your terminal:
   ```bash
   streamlit run app.py --server.address 0.0.0.0
   ```
2. Find your laptop's IP address (e.g. `192.168.1.5` on Windows using `ipconfig`, or look at the Network URL shown in the command terminal output).
3. Tell other users to open their web browsers on their phones or laptops and go to:
   `http://YOUR-LAPTOP-IP:8501` (Example: `http://192.168.1.5:8501`)

### Method B: Deploy Publicly using Streamlit Community Cloud
To make your app public so anyone in the world can access it via a link:
1. **Push your project to GitHub:** Create a new repository on GitHub and upload all the project files (`app.py`, `agent.py`, `requirements.txt`, the `data/` folder, etc.).
2. **Go to Streamlit Community Cloud:** Visit [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. **Deploy the app:**
   - Click the **"New app"** button.
   - Select your repository, branch, and set `app.py` as the main file path.
   - Click **"Deploy!"**
4. **Share the link:** Once Streamlit finishes building, copy the generated public URL and share it with your team!

---

## 13. Example Input and Output

### Input
* **School Name:** Government Primary School
* **District:** Shivamogga
* **Taluk:** Bhadravathi
* **Reporter Role:** Headmaster
* **Description:** "The student toilet is completely blocked and water sanitation pipelines are leaking, making the facility unusable."
* **Evidence:** Photo evidence uploaded, GPS coordinates = `12.9716, 77.5946`

### Output
* **Category:** Sanitation
* **Priority Level:** Urgent
* **Priority Score:** 95/100
* **Fake Risk:** Low Risk
* **Verification Status:** Report has enough supporting details
* **Recommended Action:** Deploy sanitation crew for emergency repair and cleanup of school washrooms within 24 hours.
* **Summary Text:**
  ```markdown
  School: Government Primary School in Bhadravathi Taluk, Shivamogga District.
  Issue Category: Sanitation (Urgency: Urgent, Priority Score: 95/100).
  Verification Status: Low Risk — Report has enough supporting details.
  Recommended Action: Deploy sanitation crew for emergency repair and cleanup of school washrooms within 24 hours.
  ```

---

## 14. Future Scope
* **Database Integration:** Move from static CSVs to a lightweight SQLite database to save live submissions.
* **Speech-to-Text:** Allow rural reporters to dictate complaints in regional languages (e.g., Kannada) and translate them locally.
* **Offline Mapping:** Render GPS locations on offline maps for education officers planning field visits.

---

## 15. Conclusion
The **AI School Issue Monitoring and Priority Agent** demonstrates that effective, impactful decision support systems do not require complex neural networks or expensive cloud credits. By utilizing smart rule-based logic and lightweight interface tools like Streamlit, we can create secure, robust, and localized solutions that make a tangible difference in public education management.
