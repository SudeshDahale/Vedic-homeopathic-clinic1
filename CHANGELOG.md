## [0.4.0] — 2026-05-05 | Sakshi
### Added
- Patient module complete
  - POST /patients — register with auto reg_no
  - GET  /patients — search by name/phone
  - GET  /patients/{id} — full profile
  - PUT  /patients/{id} — update any field
  - GET  /patients/{id}/history — full visit timeline
- Auth module complete
  - POST /auth/register
  - POST /auth/login — returns JWT
  - GET  /auth/me
- Role-based access working (Doctor vs Receptionist)
### Status
- Phase 5 next: Visit module (Allopathy + Homeopathy)

# Changelog — Vedic Homoeopathic Clinic

All changes documented here.
Format: [version] — date | what changed | who

---

## [0.0.1] — 2026-05-04 | Sakshi
### Added
- GitHub repo created: Vedic-homeopathic-clinic
- Branch strategy: main / dev/sakshi / dev/teammate
- Full backend folder structure created
  - src/modules: auth, patients, visits, billing, reminders, analytics
  - src/config, src/middleware, src/jobs, prisma
- .gitignore added
- .env.example template added
- CHANGELOG started
### Next
- Install dependencies (express, prisma, bcryptjs, jsonwebtoken)
- Write package.json
- Set up database schema