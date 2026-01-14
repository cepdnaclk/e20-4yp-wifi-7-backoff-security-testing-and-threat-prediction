## Sync vs Async operations in MLO

- **What it is:** These are the two main coordination methods for MLO.
    
- **How it works:**
    
    - **Synchronous (Sync):** The MLO device schedules transmissions on multiple links to start at _exactly_ the same time. This is very complex and requires tight time-keeping. It's used for true channel bonding, where one large data frame is split across links.
        
    - **Asynchronous (Async):** The links operate independently. Each link "listens-before-talk" (CSMA/CA) on its own and transmits whenever it wins channel access. This is much simpler and is used to send different, independent flows on different links.
        
- **Security Relevance:** The **Sync mode is a fragile target**. Its reliance on precise timing is a vulnerability. A **threat prediction** is an attack that injects signals to disrupt this timing (a "time-drifting" attack), which could break the synchronous bond and cause massive transmission failures