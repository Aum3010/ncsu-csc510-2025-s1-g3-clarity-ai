### Set Up the Database

# For Ubuntu 22.04

1. To install PostgreSQL, first refresh your server’s local package index: 
```
sudo apt install curl ca-certificates
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
. /etc/os-release
sudo sh -c "echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main' > /etc/apt/sources.list.d/pgdg.list"
sudo apt update
sudo apt install postgresql-18
sudo apt install postgresql-18-pgvector
```

2. After installation, verify that PostgreSQL is running and check its version:
`sudo systemctl status postgresql`

3. You should see output indicating that the service is active and running. To check the PostgreSQL version:
`sudo -u postgres psql -c "SELECT version();"`

4. Access the postgres shell by switching into postgres user.
```
sudo -i -u postgres
psql
```

5. Create our project database.
`CREATE DATABASE clarity_ai;`

6. Connect to the clarity_ai database. 
`\c clarity_ai` 

7. Enable the pgvector extension for AI embeddings `CREATE EXTENSION IF NOT EXISTS vector;`
