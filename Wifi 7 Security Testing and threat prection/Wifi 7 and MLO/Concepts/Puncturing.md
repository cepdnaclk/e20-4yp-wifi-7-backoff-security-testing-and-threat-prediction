**Wi-Fi 7 / 802.11be context**, **puncturing** is a mechanism that lets a device **skip (or “puncture”) one or more busy 20 MHz subchannels** inside a wideband channel, while still transmitting on the remaining idle subchannels. It’s a key feature to improve **throughput and spectrum efficiency** when some parts of a wide channel are congested.

Here’s a detailed explanation:

---

## 1. **The Concept**

- Wi-Fi 7 supports **very wide channels** (up to 320 MHz, i.e., 16 × 20 MHz subchannels).
    
- In practice, some subchannels may be **occupied by other devices** or have interference.
    
- Instead of deferring the **entire wideband channel**, Wi-Fi 7 can **transmit on only the free subchannels**, leaving the busy ones unused.
    
- This “skipping” of subchannels is called **puncturing**.
    

---

## 2. **How It Works**

1. **Channel is divided into 20 MHz blocks**:
    
    `[20][20][20][20] ... (up to 320 MHz)`
    
2. **Primary channel** is fixed (usually the lowest 20 MHz block).
    
3. **Secondary channels** are optional blocks added to extend bandwidth.
    
4. **During transmission**:
    
    - The device performs **CCA (Clear Channel Assessment)** on all subchannels.
        
    - **Busy subchannels** are “punctured” (skipped).
        
    - Transmission continues on **remaining idle subchannels**.
        

**Example:**

- Using a **160 MHz channel** (8 × 20 MHz blocks).
    
- Primary = 1st block, secondary = blocks 2–8.
    
- If blocks 3 and 6 are busy:
    
    `[Primary][2][X][4][5][X][7][8]`
    
    - X = punctured (skipped)
        
    - Transmission occurs on primary + idle secondary channels.
        

---

## 3. **Rules / Constraints**

- **Primary channel cannot be punctured.**
    
    - If primary is busy → defer transmission.
        
- Only **secondary channels** can be punctured.
    
- Enables **partial use of wide channels** rather than falling back to a narrower fixed bandwidth.
    

---

## 4. **Why It Matters**

- **Increases efficiency:** You don’t waste the entire wide channel because some subchannels are busy.
    
- **Improves coexistence:** Other devices using some of the 20 MHz blocks can continue operating.
    
- **Reduces latency impact:** Traffic can still flow over the free portions of the channel.
    

---

✅ **In short:**  
**Puncturing = skipping busy secondary subchannels in a wideband channel while continuing to transmit on the idle subchannels.**