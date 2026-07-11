# app.py
import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MOCK_TOKEN = "mock-jwt-token-sujanxyz"

def require_auth(f):
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth.split(" ")[1] != MOCK_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route("/healthz")
def healthz():
    return "OK", 200

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if data.get("email") == "admin@sujanxyz.hr" and data.get("password") == "password123":
        return jsonify({"token": MOCK_TOKEN})
    return jsonify({"error": "Invalid credentials"}), 401

# Dashboard
@app.route("/api/dashboard/stats")
@require_auth
def dashboard_stats():
    try:
        emp_res = supabase.table("employees").select("*").execute()
        employees = emp_res.data
        total_employees = len(employees)
        dept_res = supabase.table("departments").select("*").execute()
        total_departments = len(dept_res.data)
        pos_res = supabase.table("positions").select("*").execute()
        total_positions = len(pos_res.data)
        today = datetime.date.today().isoformat()
        att_res = supabase.table("attendance").select("*").eq("date", today).execute()
        attendance_today = len(att_res.data)
        pay_res = supabase.table("payroll").select("*").execute()
        total_payrolls = len(pay_res.data)

        # Hiring trend
        hiring = {}
        for e in employees:
            if e.get("hire_date"):
                month = e["hire_date"][:7]
                hiring[month] = hiring.get(month, 0) + 1
        sorted_months = sorted(hiring.keys())
        hiring_counts = [hiring[m] for m in sorted_months]

        # Department mix
        dept_counts = {}
        for e in employees:
            d_id = e.get("department_id")
            if d_id:
                dept_counts[d_id] = dept_counts.get(d_id, 0) + 1
        dept_labels = [d["name"] for d in dept_res.data if d["id"] in dept_counts]
        dept_data = [dept_counts[d["id"]] for d in dept_res.data if d["id"] in dept_counts]

        # Status breakdown
        status_counts = {}
        for e in employees:
            st = e.get("status", "active")
            status_counts[st] = status_counts.get(st, 0) + 1

        # Attendance 7 days
        last7 = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        att_present, att_absent = [], []
        for d in last7:
            pres = supabase.table("attendance").select("*").eq("date", d).eq("status", "present").execute()
            abs = supabase.table("attendance").select("*").eq("date", d).eq("status", "absent").execute()
            att_present.append(len(pres.data))
            att_absent.append(len(abs.data))

        # Employees by position
        emp_pos = []
        for e in employees:
            pos = next((p["title"] for p in pos_res.data if p["id"] == e.get("position_id")), "Unassigned")
            emp_pos.append({"name": e["name"], "position": pos, "profile_pic": e.get("profile_pic")})

        return jsonify({
            "total_employees": total_employees,
            "total_departments": total_departments,
            "total_positions": total_positions,
            "attendance_today": attendance_today,
            "total_payrolls": total_payrolls,
            "hiring_months": sorted_months,
            "hiring_counts": hiring_counts,
            "dept_labels": dept_labels,
            "dept_counts": dept_data,
            "status_labels": list(status_counts.keys()),
            "status_counts": list(status_counts.values()),
            "att_dates": last7,
            "att_present": att_present,
            "att_absent": att_absent,
            "employees_by_position": emp_pos
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# CRUD Employees
@app.route("/api/employees", methods=["GET"])
@require_auth
def get_employees():
    res = supabase.table("employees").select("*, departments(name), positions(title)").execute()
    data = []
    for r in res.data:
        r["department_name"] = r["departments"]["name"] if r.get("departments") else None
        r["position_title"] = r["positions"]["title"] if r.get("positions") else None
        data.append(r)
    return jsonify(data)

@app.route("/api/employees/<int:id>", methods=["GET"])
@require_auth
def get_employee(id):
    res = supabase.table("employees").select("*, departments(name), positions(title)").eq("id", id).single().execute()
    return jsonify(res.data)

@app.route("/api/employees", methods=["POST"])
@require_auth
def create_employee():
    data = request.get_json()
    res = supabase.table("employees").insert(data).execute()
    return jsonify(res.data[0]), 201

@app.route("/api/employees/<int:id>", methods=["PUT"])
@require_auth
def update_employee(id):
    data = request.get_json()
    # partial update: supabase only updates fields present in dict
    res = supabase.table("employees").update(data).eq("id", id).execute()
    return jsonify(res.data[0])

@app.route("/api/employees/<int:id>", methods=["DELETE"])
@require_auth
def delete_employee(id):
    supabase.table("employees").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"}), 200

# Departments
@app.route("/api/departments", methods=["GET"])
@require_auth
def get_departments():
    res = supabase.table("departments").select("*").execute()
    return jsonify(res.data)

@app.route("/api/departments", methods=["POST"])
@require_auth
def create_department():
    res = supabase.table("departments").insert(request.get_json()).execute()
    return jsonify(res.data[0]), 201

@app.route("/api/departments/<int:id>", methods=["PUT"])
@require_auth
def update_department(id):
    res = supabase.table("departments").update(request.get_json()).eq("id", id).execute()
    return jsonify(res.data[0])

@app.route("/api/departments/<int:id>", methods=["DELETE"])
@require_auth
def delete_department(id):
    supabase.table("departments").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"})

# Positions
@app.route("/api/positions", methods=["GET"])
@require_auth
def get_positions():
    res = supabase.table("positions").select("*, departments(name)").execute()
    data = []
    for r in res.data:
        r["department_name"] = r["departments"]["name"] if r.get("departments") else None
        emp_count = supabase.table("employees").select("*", count="exact").eq("position_id", r["id"]).execute()
        r["assigned_employees"] = emp_count.count
        data.append(r)
    return jsonify(data)

@app.route("/api/positions", methods=["POST"])
@require_auth
def create_position():
    res = supabase.table("positions").insert(request.get_json()).execute()
    return jsonify(res.data[0]), 201

@app.route("/api/positions/<int:id>", methods=["PUT"])
@require_auth
def update_position(id):
    res = supabase.table("positions").update(request.get_json()).eq("id", id).execute()
    return jsonify(res.data[0])

@app.route("/api/positions/<int:id>", methods=["DELETE"])
@require_auth
def delete_position(id):
    supabase.table("positions").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"})

# Attendance
@app.route("/api/attendance", methods=["GET"])
@require_auth
def get_attendance():
    res = supabase.table("attendance").select("*, employees(name)").execute()
    data = []
    for r in res.data:
        r["employee_name"] = r["employees"]["name"] if r.get("employees") else ""
        data.append(r)
    return jsonify(data)

@app.route("/api/attendance", methods=["POST"])
@require_auth
def create_attendance():
    res = supabase.table("attendance").insert(request.get_json()).execute()
    return jsonify(res.data[0]), 201

@app.route("/api/attendance/<int:id>", methods=["PUT"])
@require_auth
def update_attendance(id):
    res = supabase.table("attendance").update(request.get_json()).eq("id", id).execute()
    return jsonify(res.data[0])

@app.route("/api/attendance/<int:id>", methods=["DELETE"])
@require_auth
def delete_attendance(id):
    supabase.table("attendance").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"})

# Leaves
@app.route("/api/leaves", methods=["GET"])
@require_auth
def get_leaves():
    res = supabase.table("leaves").select("*, employees(name)").execute()
    data = []
    for r in res.data:
        r["employee_name"] = r["employees"]["name"] if r.get("employees") else ""
        data.append(r)
    return jsonify(data)

@app.route("/api/leaves", methods=["POST"])
@require_auth
def create_leave():
    res = supabase.table("leaves").insert(request.get_json()).execute()
    return jsonify(res.data[0]), 201

@app.route("/api/leaves/<int:id>", methods=["PUT"])
@require_auth
def update_leave(id):
    res = supabase.table("leaves").update(request.get_json()).eq("id", id).execute()
    return jsonify(res.data[0])

@app.route("/api/leaves/<int:id>", methods=["DELETE"])
@require_auth
def delete_leave(id):
    supabase.table("leaves").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"})

# Payroll
@app.route("/api/payroll", methods=["GET"])
@require_auth
def get_payroll():
    res = supabase.table("payroll").select("*, employees(name)").execute()
    data = []
    for r in res.data:
        r["employee_name"] = r["employees"]["name"] if r.get("employees") else ""
        data.append(r)
    return jsonify(data)

@app.route("/api/payroll", methods=["POST"])
@require_auth
def create_payroll():
    data = request.get_json()
    # Auto-fill from employee if not provided
    if "employee_id" in data and ("basic_salary" not in data or not data["basic_salary"]):
        emp = supabase.table("employees").select("salary, department_id, position_id").eq("id", data["employee_id"]).single().execute()
        if emp.data:
            data["basic_salary"] = data.get("basic_salary") or emp.data.get("salary", 0)
    res = supabase.table("payroll").insert(data).execute()
    return jsonify(res.data[0]), 201

@app.route("/api/payroll/<int:id>", methods=["PUT"])
@require_auth
def update_payroll(id):
    res = supabase.table("payroll").update(request.get_json()).eq("id", id).execute()
    return jsonify(res.data[0])

@app.route("/api/payroll/<int:id>", methods=["DELETE"])
@require_auth
def delete_payroll(id):
    supabase.table("payroll").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"})

if __name__ == "__main__":
    app.run(debug=True)
