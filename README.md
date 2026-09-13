# Chemical Reaction Kinetics Analyzer

An interactive, transparent web application for a Chemical Reaction Engineering
university project. It analyzes experimental concentration-time data and walks
through the full kinetics methodology — guess an order, transform, plot, fit,
accept/reject, refine, and select the physically meaningful order — rather
than just printing a final answer.

## Features

- **Integral Method** — sweeps reaction orders (0 → 3, then a fine sweep
  around the best candidate) with full transformation, regression, and
  accept/reject reasoning for every order tested.
- **Differential Method** — numerically differentiates C_A vs t (forward /
  central / backward difference, non-uniform time steps supported) and fits
  a log-log regression to get a continuous fractional order directly, plus a
  guess-and-test comparison table.
- **Autocatalytic Reaction** (A + B → 2B) — linearizes ln(C_B/C_A) vs t.
- **Reversible Reaction** (A ⇌ B) — solves forward and reverse rate constants
  from the approach to equilibrium.
- **Irreversible Reaction** (-r_A = kC_A^n) — reuses the Integral or
  Differential Method on the same dataset.
- Manual, editable data-entry table (add/remove/edit rows) **or** CSV upload.
- Full input validation (numeric, non-negative time, positive concentration,
  minimum 3 points, no NaN/∞, etc.) with friendly error messages — the app
  never crashes on bad input.
- Every graph is interactive (Plotly): experimental points, best-fit line,
  regression equation, R².
- A **Prediction Calculator** (concentration ↔ time ↔ rate) using the final
  selected kinetic model, with physical-validity checks.
- Clean, responsive UI — no coding needed to use it.

## Methodology

| Method | Rate Equation | Transformation | X-axis | Y-axis | Slope Meaning | Intercept Meaning |
|---|---|---|---|---|---|---|
| Integral (n=0) | -r_A = k | C_A = C_A0 - kt | t | C_A | m = -k | b = C_A0 |
| Integral (n=1) | -r_A = kC_A | ln C_A = ln C_A0 - kt | t | ln(C_A) | m = -k | b = ln(C_A0) |
| Integral (n=2) | -r_A = kC_A² | 1/C_A = 1/C_A0 + kt | t | 1/C_A | m = k | b = 1/C_A0 |
| Integral (n≠1) | -r_A = kC_A^n | C_A^(1-n) = C_A0^(1-n) + (n-1)kt | t | C_A^(1-n) | m = (n-1)k | b = C_A0^(1-n) |
| Differential | -r_A = kC_A^n | ln(-r_A) = ln k + n·ln(C_A) | ln(C_A) | ln(-r_A) | m = n | b = ln(k) |
| Autocatalytic | -r_A = k·C_A·C_B | ln(C_B/C_A) = k·C_T·t + ln(C_B0/C_A0) | t | ln(C_B/C_A) | m = k·C_T | b = ln(C_B0/C_A0) |
| Reversible | -r_A = kf·C_A - kr·C_B | ln[(C_A-C_Ae)/(C_A0-C_Ae)] = -(kf+kr)t | t | ln[(C_A-C_Ae)/(C_A0-C_Ae)] | m = -(kf+kr) | b = 0 |

## Project Structure

```
chemical-kinetics-analyzer/
├── backend/
│   ├── app.py                  Flask API (all routes)
│   ├── requirements.txt
│   ├── Procfile                gunicorn app:app
│   ├── runtime.txt
│   ├── .gitignore
│   └── services/
│       ├── validation.py       Input validation
│       ├── regression.py       Shared linear regression helper
│       ├── integral_method.py  Integral Method + order sweep/refine
│       ├── differential_method.py  Numerical derivative + log-log fit
│       ├── autocatalytic.py    A + B -> 2B module
│       ├── reversible.py       A <=> B module
│       ├── irreversible.py     Wraps integral/differential for -r_A = kC_A^n
│       └── prediction.py       Concentration/time/rate calculator
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── config.js           <-- set your backend URL here
│       └── main.js             All frontend logic (fetch calls to backend)
└── README.md
```

## Input Format

**Manual table:** editable rows of `Time` and `Concentration` (plus a second
concentration column for the Autocatalytic module).

**CSV upload:**

```
Time,Concentration
0,10
20,8
40,6
60,5
```

For Autocatalytic: `Time,ConcentrationA,ConcentrationB`.

## Local Installation & Execution

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python app.py
```

The API runs at `http://127.0.0.1:5000`.

### 2. Frontend

Open `frontend/js/config.js` and confirm `BASE_URL` points at
`http://127.0.0.1:5000` for local testing. Then simply open
`frontend/index.html` in a browser, or serve it locally:

```bash
cd frontend
python -m http.server 8080
```

Visit `http://127.0.0.1:8080`.

## Deployment (Render)

This project deploys as **two separate Render services**:

1. A **Web Service** for `backend/` (Flask API, via gunicorn).
2. A **Static Site** for `frontend/` (plain HTML/CSS/JS).

See the deployment walkthrough provided alongside this project for exact
step-by-step Render settings, environment variables, and how to connect the
two once both are live.

## Safety & Scope

This application only processes data typed directly into the browser or
contained in a user-uploaded CSV file. It performs no file-system scanning,
no access to credentials or environment secrets, no account automation, and
no destructive actions.
