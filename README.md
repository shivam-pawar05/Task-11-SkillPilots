# Python MySQL Read Load Balancer

## Objective
Distribute database queries between a MySQL master
and replica based on query type.

## Technologies
- Python
- MySQL
- SQLAlchemy
- PyMySQL
- python-dotenv

## Features
1. Detect SELECT queries.
2. Route reads to the replica.
3. Route writes to the master.
4. Maintain separate SQLAlchemy engines.
5. Log query routing and execution results.

## Installation

```bash
pip install -r requirements.txt
