# Smart Campus Wi-Fi Monitoring & Network Health Dashboard

A responsive web-based platform for monitoring campus network performance, collecting network health data, managing connectivity complaints, identifying recurring network issues, and supporting IT teams in investigating and resolving network problems.

**Project Type:** Academic / University Software Project
**Domain:** Campus Network Monitoring & IT Support
**Department:** Software

**Live Application:** https://smart-campus-network-monitoring.netlify.app/

---

## Project Participants

| Name              | Roll No. |
| ----------------- | -------- |
| Ahmed Memon       | 24SW019  |
| Haroon Zulfiqar   | 24SW101  |
| Syed Sayeel Abbas | 24SW116  |
| Rasool Bux        | 24SW134  |

---

## Project Overview

The **Smart Campus Wi-Fi Monitoring & Network Health Dashboard** provides a centralized platform for monitoring and managing campus network performance.

Campus users may experience slow internet, high latency, frequent disconnections, weak connectivity, or complete network outages. Traditional complaints often provide limited technical information, making it difficult for IT teams to determine the actual cause, scope, and severity of a problem.

This system addresses that challenge by combining:

* Network performance testing
* Location-based monitoring
* Network health scoring
* Complaint management
* Incident investigation
* IT support workflows
* Historical performance data
* Notifications
* Analytics and dashboards
* Role-based access

Users can test their connection at a selected campus location, view performance results, submit connectivity complaints, and track their status. IT personnel can review complaints, investigate network issues, manage assignments, record actions, and verify recovery through follow-up testing.

---

## Problem Statement

A complaint such as:

> "The Wi-Fi is very slow."

does not provide enough information for effective technical investigation.

IT support may need to know:

* Where the problem occurred
* Download and upload performance
* Network latency
* Whether other users are experiencing similar problems
* Whether the issue is temporary or recurring
* Whether the problem is isolated to a building or floor
* Whether the network has recovered after intervention

The system provides measurable network information and organizes complaints into a structured investigation and resolution workflow.

---

## Key Objectives

The project aims to:

* Measure network performance at monitored campus locations.
* Record download speed, upload speed, and latency.
* Generate an understandable network health score.
* Maintain historical network performance information.
* Allow users to submit connectivity complaints.
* Provide IT personnel with technical evidence for investigation.
* Identify recurring problems across campus locations.
* Support complaint assignment and status tracking.
* Verify network recovery through follow-up testing.
* Provide dashboards and analytics for IT teams and management.
* Notify relevant users about complaint and incident updates.
* Apply authentication and role-based authorization.

---

## Key Features

### Network Performance Testing

Users can perform a network test from their device and view measurements such as:

* Download speed
* Upload speed
* Application-level latency
* Network health score
* Test completion status

Test results are associated with a location and timestamp.

> **Measurement note:** Network measurements are performed between the user's device and the designated test endpoint. A backend-only measurement does not represent the user's actual Wi-Fi experience.

---

### Network Health Scoring

The system converts available network measurements into an understandable health score.

The scoring model considers:

| Metric         | Weight |
| -------------- | -----: |
| Download Speed |    35% |
| Upload Speed   |    20% |
| Latency        |    30% |
| Packet Loss    |    15% |

When a measurement is unavailable, the system can calculate the score using the available metrics rather than treating the missing value as zero.

### Health Categories

|  Score | Status    |
| -----: | --------- |
| 90–100 | Excellent |
|  75–89 | Good      |
|  50–74 | Fair      |
|  25–49 | Poor      |
|   0–24 | Critical  |

These thresholds can be adjusted according to campus network requirements.

The system also distinguishes unavailable or outdated measurements from actual poor network conditions through states such as **Unknown**, **Stale**, **Suspected Outage**, and **Maintenance** where applicable.

---

## Location-Based Monitoring

Network performance is associated with monitored campus locations, allowing IT teams to identify areas where connectivity problems occur repeatedly.

Users can work with location information such as:

* Building
* Floor
* Monitored location

Historical test information can then be reviewed to understand network performance patterns across different areas of the campus.

---

## Complaint Management

Users can submit network-related complaints based on their experience.

### Complaint Categories

* No Internet
* Slow Internet
* High Ping / Latency
* Frequent Disconnection
* Weak Signal
* Website or Service Unavailable
* Other

Complaints can contain information such as:

* User
* Location
* Complaint category
* Description
* Related test information
* Submission time
* Current status

### Complaint Workflow

```text
Submitted
    ↓
Reviewed
    ↓
Assigned
    ↓
In Progress
    ↓
Resolved
```

Additional statuses can be used where applicable, including:

* Awaiting User
* Awaiting External Provider
* Duplicate
* Closed
* Reopened

---

## Incident Detection & Investigation

A **complaint** represents an individual user's report, while an **incident** represents a potentially shared network problem affecting multiple users or a particular location.

The platform can use information such as:

* Recent network tests
* Multiple complaints
* Similar complaint categories
* Location-based patterns
* Existing maintenance activity
* Historical network performance

This information helps IT personnel determine whether multiple complaints may be related to a common network issue.

### Incident Workflow

```text
Suspected
    ↓
Confirmed
    ↓
Investigating
    ↓
Monitoring Recovery
    ↓
Resolved
```

---

## IT Investigation Workflow

IT personnel can investigate reported network problems through a structured workflow:

1. Review the reported complaint.
2. Examine the affected location.
3. Review recent network test results.
4. Compare current and historical performance.
5. Determine the potential scope of the issue.
6. Assign the investigation where required.
7. Record investigation notes and actions.
8. Document the probable cause.
9. Perform the required repair or maintenance.
10. Conduct a verification network test.
11. Confirm whether network performance has recovered.
12. Resolve the related complaint or incident.
13. Notify affected users where applicable.

This provides a traceable path from the original complaint through investigation and resolution.

---

## Role-Based Dashboards

The system provides different functionality according to the user's role.

### Student / Staff

Users can:

* Perform network tests
* View network health results
* View test history
* Submit complaints
* Track complaint status
* View relevant notifications

### IT Staff

IT personnel can:

* Monitor recent network tests
* Review poor-performing locations
* Manage complaints
* Investigate incidents
* Handle assigned issues
* Review location performance
* Record investigation and resolution information
* Verify network recovery

### Management

Management can review:

* Campus-wide network trends
* Frequently affected locations
* Complaint statistics
* Incident information
* Performance trends
* Areas requiring further attention

### Administration

Administrative functionality supports system-level management such as:

* User and role management
* Location management
* Network threshold configuration
* System monitoring
* Administrative controls

---

## Dashboard & Analytics

The dashboard provides an overview of network performance and support activity.

Information can be filtered by:

* Location
* Building
* Date range
* Network status
* Complaint category
* Complaint status

Network health visualization can use states such as:

* **Green** — Healthy
* **Yellow** — Degraded
* **Red** — Poor / Critical
* **Gray** — Unknown / Stale

---

## Authentication & Authorization

The application uses authenticated access and role-based permissions to separate functionality between users.

Security considerations include:

* Authentication
* Role-based access control
* Protected application routes
* API authorization
* Input validation
* Secure session handling
* Rate limiting
* Bounded network test requests
* Audit logging
* Protected administrative functionality

User-provided network measurements should also be validated because client-side measurements can be affected by the user's device, browser, network conditions, or manipulation.

---

## Notifications

The system supports communication throughout the complaint a
