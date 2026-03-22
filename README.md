# AndroTMem: From Interaction Trajectories to Anchored Memory in Long-Horizon GUI Agents



<div align="center">
<p align="center">
&nbsp&nbsp📑 <a href="https://arxiv.org/abs/2603.18429"><b>Paper</b></a>&nbsp&nbsp | &nbsp&nbsp🏠 <a href="#"><b>Project Page</b></a>&nbsp&nbsp | 🤗 <a href="#"><b>Hugging Face</b></a>&nbsp&nbsp | 🤖 <a href="#"><b>Model Scope</b></a>&nbsp&nbsp
</p>
<p align="center">
If our project helps you, please give us a star ⭐ on GitHub to support us.
<br>
<img src="https://img.shields.io/github/stars/CVC2233/AndroTMem?style=flat-square&color=E0E0E0&label=Stars" alt="GitHub stars">
</p>
</div>

## 📰 News

* **`2026-03-19`** 🌟 We are happy to release the AndroTMem. You can find the AndroTMem from [![hf_checkpoint](https://img.shields.io/badge/🤗-AndroTMem--Bench-9C276A.svg?style=flat-square)](#).


---

## 📢 Overview

**AndroTMem** is a diagnostic framework for studying **interaction memory in long-horizon Android GUI agents**.

Unlike prior work that focuses on perception or short workflows, AndroTMem highlights a key bottleneck:

> 🔥 **Failure in long-horizon tasks is primarily caused by memory breakdown, not perception errors.**
<p align="center">
  <img src="./asset/1_teaser_new_01.png" width="90%">
</p>

AndroTMem consists of:

1. **Benchmark construction**
2. **Long-horizon task design with causal dependencies**
3. **Memory-oriented evaluation (TCR)**
4. **Anchored State Memory (ASM)**
---

## ✨ Key Contributions

- 🧠 **Anchored State Memory (ASM)**  
  A structured memory mechanism that represents interaction history as **causally linked intermediate state anchors**.

- 📊 **AndroTMem-Bench**  
  A large-scale benchmark for long-horizon GUI tasks:
  - **1,069 tasks**
  - **34,473 interaction steps**
  - **Avg. 32.1 steps per task (max 65)**
  - Cross-app workflows across **50 Android apps** :contentReference[oaicite:1]{index=1}

- 🔍 **Diagnostic Evaluation Suite**
  - Shows performance degradation is dominated by **within-task memory failures**
<p align="center">
  <img src="./asset/dataset_statistics.png" width="90%">
</p>
<p align="center">
  <img src="./asset/dataset_comparison.png" width="90%">
</p>
---

## 🧩 Why AndroTMem?

Existing approaches:
- ❌ Full trajectory replay → noisy & redundant  
- ❌ Summarization → loses critical dependencies  

We propose:
- ✅ **Sparse but critical state anchors**
- ✅ **Causal dependency modeling**
- ✅ **Targeted retrieval for decision making**





---

## 🧠 Anchored State Memory (ASM)

ASM models interaction history as:

- Intermediate states (anchors)
- Causal relationships between them

Each anchor includes:
- `type` (e.g., subgoal, dependency)
- `content` (semantic info)
- `evidence` (UI grounding)
- `links` (causal dependencies)

This enables:
- 🎯 Subgoal-aware retrieval
- 🔗 Dependency-aware reasoning
- 📉 Reduced context noise

---


## 📊 Evaluation: AndroTMem-Bench

### Task Characteristics

- Long-horizon workflows (multi-step, multi-app)
- Strong **step-to-step causal dependencies**
- Requires **state reuse across distant steps**

### Task Types

- Lookup
- Compare & Decide
- Purchase / Order
- Booking
- Communication
- Sharing
- Content Creation
- Configuration

---

## 📈 Key Findings

- Performance drops significantly as step length increases
- Failures mainly due to:
  - ❌ State loss
  - ❌ State Mis-binding
  - ❌ Context drift
  - ❌ Unverified progress
  - ❌ Interruption Handling Failure
<p align="center">
  <img src="./asset/Main_Failure_Modes.png" width="90%">
</p>

ASM effectively mitigates these issues and improves:
- **TCR (Task Completion Rate)**
- **AMS (Action Matching Score)**

---


## 🔬 Results

Across 12 GUI agents (open & closed source):

- ✅ +5% ~ +30% improvement using ASM
- ✅ Strong robustness in long-horizon settings
- ✅ Better efficiency vs raw trajectory replay
<p align="center">
  <img src="./asset/history_modeling_abalation.png" width="90%">
</p>

<p align="center">
  <img src="./asset/Model_performance_line_radar.png" width="90%">
</p>


---

## 📂 Repository Structure

```bash
AndroTMem/
├── baseline
├── evaluation/       # Evaluation pipeline
├── scripts/          # Running scripts
├── assets/           # Figures (paper images)
└── README.md
```

## 📜 Citation

If you find this work useful, please cite:

```bibtex
@misc{shi2026androtmeminteractiontrajectoriesanchored,
      title={AndroTMem: From Interaction Trajectories to Anchored Memory in Long-Horizon GUI Agents}, 
      author={Yibo Shi and Jungang Li and Linghao Zhang and Zihao Dongfang and Biao Wu and Sicheng Tao and Yibo Yan and Chenxi Qin and Weiting Liu and Zhixin Lin and Hanqian Li and Yu Huang and Song Dai and Yonghua Hei and Yue Ding and Xiang Li and Shikang Wang and Chengdong Xu and Jingqi Liu and Xueying Ma and Zhiwen Zheng and Xiaofei Zhang and Bincheng Wang and Nichen Yang and Jie Wu and Lihua Tian and Chen Li and Xuming Hu},
      year={2026},
      eprint={2603.18429},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2603.18429}, 
}
```