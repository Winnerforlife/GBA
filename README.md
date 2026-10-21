# Mini LIMS API

REST API for laboratory samples, test results and an integration export for external
systems. Built with Django REST Framework.

## Stack

Python 3.12+, Django, Django REST Framework, drf-spectacular (OpenAPI / Swagger),
SQLite by default, PostgreSQL 15+ optionally.

## Quick start

### **Clone the repository**

```bash
git clone https://github.com/Winnerforlife/GBA.git
cd GBA
```

or by ssh:

```bash
git clone git@github.com:Winnerforlife/GBA.git
cd GBA
```

### **Create and activate a virtual environment**

#### **For macOS & Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

#### **For Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

### **Install dependencies**

```bash
pip install -r requirements.txt
```

### **Configure environment variables**

```bash
cp .env.example .env
```

### **Run migrations**

```bash
python manage.py migrate
```

### **Set demo data**

```bash
python manage.py seed_demo
```

### **Start the development server**

```bash
python manage.py runserver
```

- Swagger UI: http://127.0.0.1:8000/api/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/
- Django admin (optional): `python manage.py createsuperuser`, then http://127.0.0.1:8000/admin/

## Configuration

Settings are read from `.env` file (see `.env.example`)

| Variable        | Default     | Description                                                                           |
| --------------- | ----------- | ------------------------------------------------------------------------------------- |
| `SECRET_KEY`    | required    | Django secret key                                                                     |
| `DEBUG`         | `False`     | Set `True` for local development (it also makes `runserver` serve admin static files) |
| `ALLOWED_HOSTS` | empty       | Comma-separated host names                                                            |
| `DB_NAME`       | empty       | If set, PostgreSQL is used; if empty, SQLite (`db.sqlite3`)                           |
| `DB_USER`       | `postgres`  | PostgreSQL user                                                                       |
| `DB_PASSWORD`   | empty       | PostgreSQL password                                                                   |
| `DB_HOST`       | `localhost` | PostgreSQL host                                                                       |
| `DB_PORT`       | `5432`      | PostgreSQL port                                                                       |

### Running on PostgreSQL

PostgreSQL 15+ is required (Django 6). SQLite works without any setup.

## Running the tests

```bash
python manage.py test
```

## Endpoints

| Method | Endpoint                          | Description                                     |
| ------ | --------------------------------- | ----------------------------------------------- |
| POST   | `/samples`                        | Create a sample (always starts as `registered`) |
| GET    | `/samples`                        | List samples (`?status=&order_id=&client_id=`)  |
| GET    | `/samples/{sample_id}`            | Sample details                                  |
| PATCH  | `/samples/{sample_id}/status`     | Change sample status                            |
| POST   | `/results`                        | Add a result (always starts as `draft`)         |
| GET    | `/results`                        | List results (`?sample_id=&status=&parameter=`) |
| GET    | `/samples/{sample_id}/results`    | Results of one sample                           |
| PATCH  | `/results/{result_id}/approve`    | Approve a result                                |
| GET    | `/integration/export/{sample_id}` | Sample with approved results only               |

List endpoints are paginated (`count`, `next`, `previous`, `results`; 50 items per page).

## Assumptions and open questions

The task leaves some details open. Current choices, to be confirmed with the business:

- `sample_id` is **case-sensitive** (`SMP-001` and `smp-001` are different samples). Whether
  IDs should be case-insensitive is a product decision, since it depends on how IDs are
  issued (barcodes, external systems).
- A sample can have several results for the same parameter (re-measurements); there is no
  unique constraint on `(sample, parameter)`.
- A sample can be completed even if some of its results are still drafts.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions.
