# 01 - أساسيات لانج جراف (LangGraph Basics)

---

## 1. إيه هو LangGraph وليه بنستخدمه أصلاً؟

**لانج جراف (LangGraph)** هو فريم وورك معمول عشان يدير الـ Workflows المعقدة والصعبة. مش مجرد static workflow وخلاص بيمشي في اتجاه واحد، لا ده معمول مخصوص عشان:

* **الـ State Management (إدارة الحالة):** هو عبارة عن **Stateful Workflow**، يعني طول ما إحنا ماشيين في الفلو، الـ State بتفضل معانا وعارفين كل Node وصل لحد فين وموجود جواه إيه.
* **الـ Loops والرجوع لورا:** لو عايز تعمل Loop وترجع لنود سابقة تعيد خطوة أو تعدل حاجة، لانج جراف بيسمحلك بده بكل سهولة.
* **الـ Human-in-the-Loop:** تقدر توقف الفلو في النص عشان تاخد رأي أو تأكيد من إنسان (Human Intervention) وبعدين تكمل.
* **التكامل مع LangChain:** الـ Building Blocks اللي جوة النودز (زي الموديل، الـ Prompts، الـ Tools) ممكن تعملها بـ **LangChain** عادي جداً، ولانج جراف بقى هو المايسترو اللي **بيمانج الفلو (Flow)** بتاع السيستم كله.

---

## 2. الـ State والـ Reducers (مشكلة الـ Overwrite)

### المشكلة:
في العادي جوة لانج جراف، الـ State بيحصل لها **Overwrite** مش تعديل ولا Append.
> يعني لو عندك في الـ State مفتاح اسمه `name`، وكتبت فيه "Gohar" في أول نود، وجيت في تاني نود بعت له "Ahmed"، القيمة القديمة هتروح في داهية ومش هتلاقي غير "Ahmed".

### الحل: الـ Reducer
هنا بقى بيظهر دور الـ **Reducer**؛ هو اللي بيخليني أتحكم في إزاي الـ State تتحدث وتعمل Append للداتا بدل ما تمسح القديم:

1. **Custom Reducer:** دالة أنا اللي بحددها، مثلاً أستخدم `operator.add` عشان أعمل دمْج (Concatenate) للقوائم.
2. **Built-in Reducer:** حاجات جاهزة جوة لانج جراف نفسه، وأشهرهم `add_messages`، وده ميزته إنه بيدير رسايل الشات ومبيكررش الرسايل اللي ليها نفس الـ ID بل بيحدثها بذكاء.

```python
from typing import Annotated
from typing_extensions import TypedDict
import operator
from langgraph.graph.message import add_messages

class State(TypedDict):
    # دي لو اتعدلت هيتعمل لها Overwrite عادي
    user_name: str
    
    # دي هيتعمل لها Append وتتجمع على اللي فات بفضل operator.add
    history: Annotated[list[str], operator.add]
    
    # دي بتدير الشات والرسايل من غير ما تضيع الرسايل القديمة
    messages: Annotated[list, add_messages]
```

---

## 3. إزاي بنبني الـ State؟ (State Schema)

بنعمل كلاس عادي جداً يمثل الـ State، وعندنا طريقتين نكتبه بيهم:

1. **طريقة الـ `TypedDict`:**
   * دي الطريقة الخفيفة والسريعة، بتحدد أسماء الحقول وأنواعها وخلاص.
   ```python
   from typing_extensions import TypedDict

   class State(TypedDict):
       name: str
       greeting: str
   ```

2. **طريقة الـ `Pydantic BaseModel`:**
   * بتعمل كلاس يورث من `BaseModel`، وبنستخدمها لو عايزين Validation قوي للداتا وقيم افتراضية.
   ```python
   from pydantic import BaseModel

   class State(BaseModel):
       name: str
       greeting: str = ""
   ```

---

## 4. تكوين الجراف: الـ Nodes والـ Edges

أي جراف بنبنيه بيتكون من:

### 1) الـ Nodes (العقد):
* دي عبارة عن دوال بايثون عادية جداً (Functions).
* بتاخد الـ `state` الحالية كمدخل، وتنفذ شغلها، وبترجع Dictionary فيه الجزء اللي عايزة تحدثه في الـ State.

```python
def greeting(state: State):
    return {
        "greeting": f"Hello {state['name']}"
    }
```

### 2) الـ Edges (المسارات والروابط):
* الجراف بيبدأ من نود اسمها `START` وبينتهي عند `END`.
* **مسار ثابت (One-direction / Normal Edge):** يعني النودز بتسلم لبعضها ورا بعض مباشرة:
  ```python
  builder.add_edge(START, "greet")
  builder.add_edge("greet", END)
  ```
* **مسار مشروط (Conditional Routing):**
  * ده بقى اللي بيخليني أقرر: هروح فين؟ هعمل Loop وارجع تاني لنود تانية؟ ولا هقفل الجراف؟
  * القرار ده ممكن يتاخد بطريقتين:
    1. **Static Function:** دالة برمجية عادية فيها `if / else` بتشوف قيمة معينة في الـ State وتقرر الـ Route.
    2. **LLM Model:** نخلي موديل الذكاء الاصطناعي هو اللي يقرر الأكشن، زي مثلاً هل يحتاج ينادي Tool معينة ولا يرد على المستخدم علطول.

```python
def decide_next_step(state: State):
    if state.get("need_more_info"):
        return "ask_user"
    return "finish"

builder.add_conditional_edges(
    "process_node",
    decide_next_step,
    {
        "ask_user": "ask_user_node",
        "finish": END
    }
)
```

---

## 5. مرحلة الـ Compile وبداية التشغيل

بعد ما ترسم النودز والـ Edges في الـ `builder`، بتعمل خطوة الـ **Compile** عشان تبني الجراف ويبقى جاهز للتنفيذ:

```python
graph = builder.compile()
```

---

## 6. طرق تشغيل الجراف: `invoke` ولا `stream`؟

عندك طريقتين أساسيتين عشان ترن الجراف بتاعك:

1. **الـ `invoke` (كله مرة واحدة):**
   * بتبعت المدخلات، وتستنى الجراف يخلص كل خطواته ويرجعلك الـ Final State كاملة في الآخر.
   ```python
   result = graph.invoke({"name": "Gohar"})
   print(result)
   ```

2. **الـ `stream` (خطوة بخطوة أول بأول):**
   * ده ممتاز لو عايز تعرض للمستخدم إيه اللي بيحصل لحظياً، بيرجعلك تحديثات كل Node أول ما تخلص شغلها.
   ```python
   for event in graph.stream({"name": "Gohar"}):
       print(event)
   ```

---

## 7. إزاي ترسم الجراف وتشوف شكله بعينك؟ (Visualization)

عشان تتأكد إن التوصيلات والـ Edges صح ومفيش نود تايهة، تقدر تطبع رسمة الجراف في الـ Terminal أو كصورة:

```python
# رسم الجراف كنص في التيرمينال (ASCII)
print(graph.get_graph().draw_ascii())

# أو حفظه كصورة Mermaid PNG
from IPython.display import Image, display
display(Image(graph.get_graph().draw_mermaid_png()))
```

---

## 8. إيه الفرق بين الـ Workflow والـ Agent؟

* **الـ Workflow (مسار العمل):**
  * خطوات ثابتة وأنا عارفها بالمللي من قبل ما الكود يشتغل.
  * عارف إيه اللي هيحصل خطوة بخطوة، فسهل جداً إني أتوقعه (Predictable) وأعمل له Debugging وأمشي وراه من أوله لآخره.

* **الـ Agent (الوكيل الذكي):**
  * الموضوع هنا مختلف وأكثر مرونة (More Flexible).
  * أنا مش عارف مسبقاً السيناريو هيمشي إزاي بالتفصيل؛ لأن الـ LLM Model هو اللي بياخد القرار في وقت التشغيل (Runtime) ويختار يروح لأنهي أداة ويوجه الفلو إزاي حسب الحالة والمدخلات.

---
