\# ☁️ Cloud File Storage System



A beginner-friendly cloud file storage web application built using Flask, SQLite, and Microsoft Azure Blob Storage.



Users can register, log in securely, upload files to Azure Blob Storage, download their files, and delete them.



\---



\## 🚀 Features



\- User registration and login

\- Password hashing

\- Session-based authentication

\- Secure file ownership

\- File upload to Azure Blob Storage

\- File download from Azure Blob Storage

\- File deletion from Azure Blob Storage

\- SQLite database for user and file metadata

\- Responsive web interface

\- Environment variables for sensitive configuration



\---



\## 🛠️ Technologies Used



\- Python

\- Flask

\- Flask-SQLAlchemy

\- SQLite

\- Microsoft Azure Blob Storage

\- HTML5

\- CSS3

\- Git \& GitHub



\---



\## 🏗️ Project Architecture



```text

User Browser

&#x20;    |

&#x20;    v

Flask Web Application

&#x20;    |

&#x20;    +--------------------+

&#x20;    |                    |

&#x20;    v                    v

SQLite Database      Azure Blob Storage

&#x20;    |                    |

&#x20;    v                    v

User \& File          Actual Files

Metadata

