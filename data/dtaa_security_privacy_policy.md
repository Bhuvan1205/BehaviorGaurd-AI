# DTAA Corporation
## Information Security & Data Privacy Policy
### Document Reference: DTAA-SEC-POL-001 | Version 3.2 | Effective Date: January 1, 2026
### Classification: Internal Use Only

---

## 1. Purpose and Scope

This policy establishes the information security and data privacy standards governing all employees, contractors, and third parties who access DTAA Corporation systems, data, or facilities. Compliance with this policy is mandatory and non-negotiable. Violations may result in disciplinary action up to and including immediate termination and referral for criminal prosecution.

This policy applies to:
- All full-time and part-time employees regardless of role or seniority
- Contractors, consultants, and temporary staff
- All DTAA-owned or DTAA-managed systems, networks, devices, and data
- All data created, processed, stored, or transmitted in connection with DTAA business

---

## 2. Data Classification

DTAA classifies all corporate data into four tiers. Every employee must understand which tier applies to data they handle.

### 2.1 Tier 1 — Public
Information approved for external distribution. No restrictions on sharing.
Examples: marketing materials, published press releases, job postings.

### 2.2 Tier 2 — Internal
Information intended for internal use only. May be shared freely within DTAA but must not leave the organization without authorization.
Examples: internal memos, project plans, team communications, general operational data.

### 2.3 Tier 3 — Confidential
Sensitive business information. Access is limited to employees with a documented business need. Sharing externally requires written approval from a department head and the CISO.
Examples: client contracts, pricing structures, personnel records, financial projections, vendor agreements, proprietary processes.

### 2.4 Tier 4 — Restricted
Highest sensitivity. Access is strictly controlled on a need-to-know basis. Any external sharing is prohibited without written approval from C-level leadership and Legal.
Examples: trade secrets, unpublished research data, active patent applications, system architecture documentation, security infrastructure configurations, privileged access credentials, raw experimental formulas, full client databases with contract values.

**Violation of Tier 3 or Tier 4 data handling rules constitutes a serious breach of this policy and will result in immediate investigation and likely termination.**

---

## 3. Acceptable Use of Corporate Email

### 3.1 General Principles
Corporate email systems are provided for business purposes. Limited personal use is permitted provided it does not interfere with job responsibilities, consumes minimal resources, and complies with all provisions of this policy.

### 3.2 Prohibited Email Activities
The following uses of corporate email are strictly prohibited:

**(a) Sending confidential or restricted data to personal email accounts.**
Employees must never forward, attach, or transmit any Tier 3 or Tier 4 data to personal email accounts (including but not limited to Gmail, Yahoo, Outlook personal, ProtonMail, Tutanota, or any other non-corporate email service), regardless of the stated reason. "Working from home" or "personal backup" does not constitute authorization.

**(b) Transmitting proprietary information to external parties without authorization.**
No client data, pricing information, research data, formulas, methodology documentation, system configurations, access credentials, or employee information may be sent to external parties — including competitors, recruiters, or third-party vendors — without written approval from a department head and the Legal department.

**(c) Using corporate email to facilitate outside employment negotiations.**
Employees must not use corporate email systems to conduct job searches, respond to competitor recruitment inquiries, negotiate employment terms with other organizations, or share DTAA information with prospective employers.

**(d) Sending bulk exports of corporate data externally.**
Exporting and transmitting large datasets — including client lists, user directories, access logs, configuration files, or research databases — to any external destination without explicit written authorization constitutes data exfiltration and will be treated as a serious security incident.

**(e) Sharing access credentials via email.**
Usernames, passwords, API keys, or any form of authentication credential must never be transmitted via email under any circumstances, whether internally or externally.

**(f) Sending data to encrypted or anonymous email services for the purpose of circumventing monitoring.**
The use of ProtonMail, Tutanota, or similar encrypted email services for transmitting corporate data is prohibited. These services are often used to conceal unauthorized data transfers and will be treated as a policy violation regardless of the content.

### 3.3 Attachment Controls
Attachments containing Tier 3 or Tier 4 data must be encrypted using DTAA-approved encryption tools before transmission, even when sent internally. Unencrypted attachments containing sensitive data sent to external addresses constitute a policy violation.

### 3.4 External Recipient Monitoring
All emails sent to external domains are subject to automated monitoring for data loss prevention (DLP) purposes. Employees should have no expectation of privacy when using corporate email systems.

---

## 4. Data Handling and Intellectual Property

### 4.1 Ownership of Work Product
All work, inventions, discoveries, research, methodologies, formulas, software, and other intellectual property created by employees during their employment — whether during working hours or personal time, whether using company equipment or personal equipment — are the exclusive property of DTAA Corporation, provided the work relates to the company's business activities or areas of research.

Employees may not claim personal ownership of research data, experimental results, proprietary formulas, or methodology documentation developed in the course of their employment.

### 4.2 Research Data Controls
All research data, experimental results, raw datasets, and analytical findings produced by DTAA employees are classified at minimum as Tier 3 Confidential. Unpublished research, active patent applications, and proprietary formulas are classified as Tier 4 Restricted.

Researchers must not:
- Export raw research data to personal storage devices or personal email accounts
- Share unpublished methodology documentation with external parties including academic collaborators without prior approval from Legal and the department head
- Discuss proprietary research details with employees of competitor organizations
- Contact competitor organizations regarding research collaboration without formal authorization through the Business Development department

### 4.3 Client Data Controls
All client information — including names, contact details, contract values, renewal dates, pricing terms, account notes, and any information derived from client relationships — is classified as Tier 3 Confidential or Tier 4 Restricted depending on sensitivity.

Employees must not:
- Copy client lists or account databases to personal devices or email accounts
- Share client information with competitor organizations under any circumstances
- Use client relationships developed during DTAA employment to benefit a competing organization, either during employment or after departure
- Retain copies of client data after employment termination

Violation of client data controls may expose both the employee and DTAA to legal liability under applicable data protection and trade secret laws.

### 4.4 System Configuration and Security Data
IT infrastructure documentation, network topology diagrams, firewall configurations, VPN credentials, privileged access account lists, security incident reports, and authentication logs are classified as Tier 4 Restricted.

IT and Security department employees must not:
- Export system configuration files, access logs, or security reports to personal email accounts
- Share privileged account information with external parties
- Provide network architecture details or security infrastructure information to outside parties including prospective employers
- Attempt to access or modify audit or monitoring logs

---

## 5. Privileged Access Management

### 5.1 Principle of Least Privilege
All employees are granted the minimum level of system access required to perform their job function. Access beyond this baseline requires formal approval from the relevant department head and must be logged in the Privileged Access Management (PAM) system.

### 5.2 Credential Management
- Employees must not share login credentials with colleagues under any circumstances
- Service accounts and shared administrative credentials must be managed exclusively through the PAM system
- Credential export requests must be submitted through the formal IT request process and require manager approval
- Employees leaving the organization will have all access revoked within 4 hours of their resignation or termination being recorded in HR systems

### 5.3 Administrative Access Controls
Employees with elevated system privileges (domain administrators, database administrators, security analysts with SIEM access) are subject to enhanced monitoring. Actions taken using privileged accounts are logged and audited on a continuous basis.

---

## 6. Monitoring and Audit Rights

### 6.1 Employee Monitoring
DTAA reserves the right to monitor all activity on company-owned systems, networks, and devices. This includes but is not limited to:
- Email content, attachments, and recipient addresses
- File access, creation, modification, and deletion
- Network traffic and internet activity
- System login and logout events
- USB and external device connections
- Application usage

Employees have no expectation of privacy when using DTAA systems.

### 6.2 Log Retention
All system activity logs are retained for a minimum of 24 months. Employees may not request deletion of their own activity logs. Requests to purge email records or system logs — regardless of the stated justification — will be flagged as a potential security concern and reported to the CISO.

### 6.3 DLP (Data Loss Prevention) Controls
Automated DLP systems scan all outbound email for sensitive content patterns. Emails flagged by DLP may be quarantined pending review. Employees who repeatedly trigger DLP alerts will be subject to additional monitoring and investigation.

---

## 7. Incident Reporting

### 7.1 Mandatory Reporting
All employees must immediately report the following to the Security department (security@dtaa.com) or the CISO:
- Accidental transmission of sensitive data to incorrect recipients
- Suspected unauthorized access to systems or data
- Lost or stolen company devices
- Phishing attempts or social engineering approaches
- Any external contact from competitor organizations requesting proprietary information

### 7.2 Non-Retaliation
Employees who report security incidents in good faith will not face retaliation. Early reporting significantly reduces the impact of security incidents and will be treated as a mitigating factor in disciplinary proceedings.

---

## 8. Offboarding and Data Handling at Separation

### 8.1 Access Revocation
Upon resignation or termination, all system access will be revoked promptly. The standard timeline is within 4 hours of HR recording the departure. In cases of immediate termination for cause, access may be revoked simultaneously with notification.

### 8.2 Data Retention at Separation
Departing employees must not:
- Copy, download, or transmit any company data — including client lists, research data, pricing information, or contact databases — in the period leading up to their departure
- Retain any company data on personal devices after their last day
- Use company data for the benefit of a new employer or competitive activity after departure

Employees may retain only personal items clearly unrelated to DTAA business.

### 8.3 Pre-Departure Behavior
Unusual data access or transmission activity in the weeks preceding a resignation — including bulk downloads, external email transmissions of large files, or access to systems outside normal job function — will be treated as potential data exfiltration and investigated accordingly.

---

## 9. Consequences of Policy Violations

Policy violations are classified by severity:

### Level 1 — Minor Violation
Examples: accidental transmission of internal data, minor acceptable use breach.
Consequence: formal written warning, mandatory security training.

### Level 2 — Moderate Violation
Examples: sending Tier 3 confidential data to personal email once, forwarding client contact details externally without authorization.
Consequence: written warning, additional monitoring, possible suspension pending investigation.

### Level 3 — Serious Violation
Examples: repeated unauthorized external transmission of sensitive data, deliberate sharing of client lists or research data with a competitor, transmitting system access credentials externally, exporting bulk data to personal accounts.
Consequence: immediate termination, potential civil and criminal referral, notification of affected clients.

### Level 4 — Critical Violation
Examples: deliberate exfiltration of Tier 4 Restricted data, sharing trade secrets or unpublished research with a competitor organization, coordinated data theft in connection with outside employment.
Consequence: immediate termination, mandatory referral to law enforcement, civil lawsuit for damages, non-compete and NDA enforcement.

---

## 10. Specific Role-Based Obligations

### 10.1 IT Administrators and Security Personnel
Employees with administrative access to infrastructure systems carry elevated responsibilities. In addition to all general policy requirements:
- All privileged actions must be performed through approved channels and are subject to continuous audit
- Any export of system logs, configuration files, or access credential databases requires written authorization from the CISO
- Probing colleagues for credentials or access permissions outside of formal IT request processes is prohibited
- Contact with external security recruiters using DTAA-provided email is prohibited

### 10.2 Research and Development Personnel
- All experimental data, formulas, and methodology documentation remain company property
- External collaboration on DTAA-funded research requires approval from Legal and the department head
- Patent applications and IP disclosures must be submitted through the Legal department — employees must not independently file or disclose inventions developed during their employment
- Contact with competitor research personnel regarding ongoing DTAA projects is prohibited without formal authorization

### 10.3 Sales Personnel
- Client account information, contract values, pricing structures, and renewal calendars are Tier 3 Confidential
- Employees may not copy client databases to personal devices or accounts at any time, including during notice periods
- Using knowledge of client relationships or accounts to benefit a competing employer constitutes a breach of fiduciary duty and may violate non-solicitation agreements
- Discount authority matrices and pricing tier documents are classified as Tier 3 Confidential and must not be shared externally

---

## 11. Policy Acknowledgment

All employees are required to acknowledge receipt and understanding of this policy annually. By accessing DTAA systems, employees implicitly acknowledge that they have read, understood, and agreed to comply with this policy in its entirety.

Questions regarding this policy should be directed to:
- **Information Security:** ciso@dtaa.com
- **Legal and Compliance:** legal@dtaa.com
- **HR (policy administration):** hr@dtaa.com

---

*DTAA Corporation | Information Security & Data Privacy Policy | DTAA-SEC-POL-001 v3.2*
*Next review date: January 1, 2027*
