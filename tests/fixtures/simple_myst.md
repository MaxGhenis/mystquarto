# My document

This is a MyST document with {cite}`smith2020` references.

```{code-cell} python
:tags: [hide-input]

import numpy as np
x = np.linspace(0, 1, 100)
```

```{figure} images/plot.png
:name: fig-plot
:width: 80%

My figure caption.
```

As shown in {numref}`fig-plot`, the result from {eq}`energy` is clear.

```{math}
:label: eq-energy

E = mc^2
```

:::{note}
This is an important note.
:::

:::{warning}
Be careful with this.
:::

```{bibliography}
:style: unsrt
```

The value is {eval}`compute_value()`.

See {doc}`methods` for more.

```{tableofcontents}
```
