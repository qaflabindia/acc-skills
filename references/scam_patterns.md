# AFCC Scam Pattern Reference

Pattern recognition is adversarial financial cognition — not regex detection.
Each pattern includes: core narrative, signal cluster, risk amplifiers, and
what the scammer is trying to prevent you from doing (the "friction target").

---

## P-01: Digital Arrest / Fake Police / CBI / ED Demand

**Core Narrative**
"You are under investigation. Your number/Aadhaar/account is linked to money
laundering / drug trafficking / illegal activity. To avoid arrest, you must
transfer X immediately. Do not tell anyone."

**Signal Cluster**
- Authority: police, CBI, ED, Customs, Telecom Dept claimed
- Medium: phone call, sometimes WhatsApp video
- Urgency: extreme — "arrest warrant in 2 hours"
- Secrecy: explicit — "do not tell family / bank"
- Beneficiary: new unknown individual or mule account
- Amount: high (₹50,000 to several lakhs)
- Legitimacy claim: official-sounding case number, "officer name"

**What the scammer blocks**
Independent verification. Any conversation with family. Any call-back to
the real institution. Any cooling period.

**Cognitive triggers**
- `authority_claimed = true` + `authority_verified = false`
- `secrecy_requested = true`
- `urgency_manipulation_score > 0.85`
- `beneficiary_trust < 0.10`

**AFCC verdict**: BLOCK (hard). Override disabled.

---

## P-02: Fake Bank Officer / KYC Expiry Block

**Core Narrative**
"Your account will be blocked / KYC has expired / suspicious transaction
detected. Share OTP / click this link / transfer to safe account to protect
your funds."

**Signal Cluster**
- Authority: bank official, RBI officer claimed
- Medium: phone (spoofed bank number), SMS
- Urgency: "account blocked in 30 minutes"
- Action requested: OTP sharing, clicking link, or "safe account transfer"
- Beneficiary: claimed to be internal bank account (actually mule)

**What the scammer blocks**
Hanging up and calling the bank directly. Any delay.

**Cognitive triggers**
- `authority_claimed = true` + `communication_context = phone`
- `urgency_manipulation_score > 0.70`
- `reason_given` contains: safe account / KYC / OTP / block / verify

**AFCC verdict**: BLOCK. Escalate to bank fraud helpline (official number only).

---

## P-03: Investment / Guaranteed Return Fraud

**Core Narrative**
"Join our exclusive trading group / stock tips / crypto scheme. Guaranteed
30% monthly returns. Limited seats. Transfer now to start."

**Signal Cluster**
- Beneficiary: individual account or crypto wallet (not institution)
- Amount: "initial investment" framing
- Promise: guaranteed returns, insider tips, exclusive opportunity
- Urgency: "offer closes today" / "limited slots"
- Social proof: fake testimonials, WhatsApp group screenshots

**What the scammer blocks**
Any independent verification of the scheme or entity.

**Cognitive triggers**
- `payment_type = investment` + `beneficiary_trust < 0.30`
- Reason contains: guaranteed / returns / trading group / crypto / exclusive
- `urgency_manipulation_score > 0.50`

**AFCC verdict**: ESCALATE → user verification. High speculative necessity score.

---

## P-04: Refund / Overpayment Scam

**Core Narrative**
"We accidentally sent you ₹X extra. Please return it immediately. Here is
a QR code / link. Enter the refund amount."

**Signal Cluster**
- Initiator: inbound call or message claiming overpayment
- Action: user asked to initiate payment (not receive)
- Medium: QR code, UPI deep link, payment app redirect
- Urgency: moderate — "our accounts team is waiting"

**What the scammer blocks**
User checking their own account first. Any delay to verify.

**Cognitive triggers**
- Inbound demand to pay back an amount not in user's own records
- `communication_context = inbound_call`
- New beneficiary + refund framing

**AFCC verdict**: DELAY. Verify independently — check bank statement first.

---

## P-05: Family Emergency Impersonation

**Core Narrative**
"Mum, it's [child's name]. I've been arrested / in accident / lost phone.
Please transfer X immediately. I'll explain later. Don't call my old number."

**Signal Cluster**
- Caller claims to be family member
- New number / unfamiliar contact
- Prevents verification: "don't call my old number"
- Urgency: extreme — medical / legal emergency
- Amount: moderate to high

**What the scammer blocks**
Calling the real family member on their known number.

**Cognitive triggers**
- `communication_context` = new number claiming family identity
- `urgency = extreme` + `secrecy_requested = true`
- Beneficiary not in existing contact history

**AFCC verdict**: DELAY. Verify by calling known number directly before any transfer.

---

## P-06: OTP / Remote Access Extraction

**Core Narrative**
"I'm from [bank/company] tech support. Your account has a problem. Please
install [app] so I can help remotely / share the OTP I just sent you."

**Signal Cluster**
- OTP sharing requested
- Remote access app installation requested (AnyDesk, TeamViewer, etc.)
- Authority: tech support / bank / UPI support claimed
- Note: no legitimate institution ever asks for OTP or remote access

**Cognitive triggers**
- OTP sharing mentioned in reason
- Remote access app name in communication context
- `authority_claimed = true` (tech support / bank support)

**AFCC verdict**: BLOCK immediately. OTP sharing = account compromise.

---

## P-07: Mule Account Transfer

**Core Narrative**
This is less a direct demand and more a structural pattern: the scam already
succeeded elsewhere, and the user's account is being used as a relay.

**Signal Cluster**
- User received unexpected funds from unknown sender
- Being asked to immediately forward those funds to another account
- Amount matches what was received (minus a "commission")
- Framed as "business opportunity" or "money transfer job"

**Cognitive triggers**
- `beneficiary` = individual (not institution)
- `reason_given` = received funds + forward request
- `payment_type = transfer`

**AFCC verdict**: BLOCK. Do not forward received funds. Report to bank.

---

## P-08: Lottery / Prize / Inheritance Unlock

**Core Narrative**
"You've won a prize / inherited money from overseas. Pay processing fee /
tax / customs to release the funds to your account."

**Signal Cluster**
- User did not enter any lottery
- Overseas funds / foreign inheritance narrative
- Payment requested before receiving anything
- Amount: "processing fee" (₹5,000–₹50,000)

**Cognitive triggers**
- `reason_given` contains: prize / won / inheritance / release fee
- `beneficiary_trust < 0.20`
- `obligation_priority = 0` (no legitimate obligation)

**AFCC verdict**: BLOCK. No legitimate prize requires upfront payment.

---

## P-09: Romance / Emotional Manipulation Transfer

**Core Narrative**
Long-duration relationship established online. Emotional trust built over
weeks/months. Then: "I'm in trouble / stuck / need money. I'll repay when I visit."

**Signal Cluster**
- Beneficiary met online (dating app, social media)
- Prior relationship established (weeks/months of contact)
- Never met in person (or photo-ID only)
- Escalating financial requests over time
- Medical / visa / flight / emergency framing

**Cognitive triggers**
- `beneficiary_trust` built on online-only relationship
- Escalating amount pattern over time
- `execution_confidence` should drop as pattern repeats

**AFCC verdict**: ESCALATE. Trusted contact review before any transfer.

---

## Scam-Agnostic Red Flags (any combination elevates risk)

| Signal | Risk amplifier |
|--------|---------------|
| "Do not tell anyone / family / bank" | +0.40 fraud_probability |
| "Transfer immediately or [consequence]" | +0.35 urgency_manipulation_score |
| New beneficiary + first contact | +0.30 fraud_probability |
| Authority claimed + phone-initiated | +0.35 fraud_probability |
| Request between 11PM–6AM | +0.20 fraud_probability |
| User shows signs of panic/distress | +0.25 panic_probability |
| "This is your last chance" phrasing | +0.30 urgency_manipulation_score |
| Amount is round number (₹1L, ₹2L, ₹5L) | +0.10 fraud_probability |

---

## The Meta-Pattern

Every scam shares one structural goal:
**prevent the victim from verifying, waiting, or asking anyone.**

AFCC response:
- Urgency → mandatory delay
- Secrecy → escalate to trusted contact
- Authority → independent callback required
- New beneficiary → quarantine

These are not conveniences. They are constitutional friction.
