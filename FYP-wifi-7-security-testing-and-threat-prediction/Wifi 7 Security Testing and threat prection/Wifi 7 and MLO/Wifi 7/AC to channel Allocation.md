## AC to link allocation

- **What it is:** "AC" stands for **Access Category**. Wi-Fi uses ACs to prioritize traffic (e.g., AC_VO for Voice, AC_VI for Video, AC_BE for Best Effort). **AC to link allocation** is a policy used in Multi-Link Operation (MLO) to decide which physical radio link (e.g., the 5 GHz link or the 6 GHz link) should carry which traffic category.
    
- **How it works:** A Wi-Fi 7 AP or device can create rules, such as sending all high-priority voice (AC_VO) traffic on the most stable link, while using both links simultaneously for high-throughput data (AC_BE).
    
- **Security Relevance:** This allocation logic is a new attack surface. A **threat prediction** would be an attacker intentionally congesting one link (e.g., the 5 GHz band) with low-level traffic to trick the AP's policy into moving high-priority traffic (like a security camera feed) to a link that the attacker is better positioned to jam or monitor. **Security testing** must validate that these allocation policies are resilient and don't make poor decisions when under duress.