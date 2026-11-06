# Evidence note

Every number below was recomputed from the case dataset (5,000 leads, 368 activations). Scripts are in the team's analysis folder; the figures are reproducible from `data/`. Where a result is directional or based on small samples, it says so.

## Funnel and cost
5,000 leads -> 3,406 -> 1,974 -> 861 -> 588 -> **368 activated (7.4%)**. Average 17.6 days from lead to activation, 3.0 follow-up calls per lead. Sales and marketing spend Rs 5.54M, so **about Rs 15.1k per activation**.

| Segment | Share of leads | Conversion | Cost per activation | Churn |
|---|---|---|---|---|
| Micro retail and services | 54% | 4.1% | Rs 20.0k | 22.7% |
| Professional offices | 25% | 11.1% | Rs 10.7k | 13.8% |
| Small multi-site | 15% | 11.0% | Rs 15.6k | 10.8% |
| Small manufacturers | 6% | 12.8% | Rs 15.3k | 8.1% |

Field sales and partners take 85% of spend for 56% of activations (Rs 21-24k each); inbound, referral, website and WhatsApp cost Rs 4-6k each.

## Why leads dropped (4,632 lost)
- Process friction 36% (owner had no time for a visit, visit not scheduled, quote too complex or slow, install delayed, missing or mismatched documents, paperwork, payment failed).
- Could not reach the owner 24%.
- Price, demand, competitor 40%.

A figure of "44% process friction" circulated early in the work and **does not reproduce** under a clean definition. We use 36%.

## What the rules engine found in the data
- **48 of 368 activated bundles broke a hard catalogue rule** (city tier 24, GST-only product without an active GSTIN 21, below minimum employees 8). Violating bundles did *not* churn more (8.9% vs 16.3%), so we do not claim they hurt retention.
- **901 of 5,000 leads (18%) asked for something not buyable as asked** (hard rules, including registry GSTIN status). If only the "has a GSTIN" flag is used, the figure is 769. Those leads convert at 5.0% vs 7.9%.
- 22 activated customers had a Cancelled or Suspended GSTIN; 30 had none.

## Regional language and tier-2 cities (directional)
- English and Hindi leads convert at about 8.0% and 7.9%; the other eight languages together at about 6.2%. Tamil 4.3%, Punjabi 4.2%, Kannada 5.1% (n is 83 to 253 per language, so single languages are noisy).
- Tier-1 cities convert at 8.6% (Rs 13.5k per activation); tier-2 at 6.1% (Rs 17.4k).
- Reading: self-serve in regional languages and tier-2 is where the gap is, which is why Hindi ships first and other languages are next. It is not proof that language causes the gap.

## Payback on a digital activation
Cost per activation divided by average monthly billing: micro about 8.0 months, professional 1.6, manufacturers 0.8, multi-site 0.5. Micro is where cheap self-serve matters most; larger accounts pay back fast even with field sales.

## Impact estimate (assumption, not a forecast)
If self-serve lifts conversion from 7.4% to 12%, that is 600 activations (+232), about Rs 9.2k per activation, roughly **Rs 3.4 crore of annual billing before churn, discounts and added cost**.

## Smart KYC
- GSTIN checksum (mod 36) verified on all 3,534 registry entries. A single-character typo is caught by the checksum 100% of the time on every entry tested.
- OCR is read several ways; a reading is accepted only if the checksum is valid **and** the number is in the registry. Matching is on the registration number, never the name. Near-misses (K06, K10) are blocked, never auto-corrected.
- **12 of 12 specimen applicants give the expected outcome** (about 3 seconds each on a CPU). The expected outcomes were set by reading the images ourselves, so this is a regression test and **not a blind benchmark**.
- K04 (blurred) cannot be read: the system asks for a clearer photo, or continues on the typed GSTIN with a review flag.

## Propensity model (back-office "call first" list)
Logistic regression on fields known at lead creation. ROC-AUC 0.714 (5-fold) and 0.718 on a chronological holdout. Top-decile leads convert at 17-18% vs 7.4% overall. Modest: it **prioritises** calls and never rejects a lead.
