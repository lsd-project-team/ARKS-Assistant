"""查询每产出一项才执行foreach正文；提前退出不会先物化余下输入。"""

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import text
from app.modules.action_timing.source_queries import QueryExecution
from app.modules.action_timing.source_scopes import local_scope, restore


class QueryForeach(QueryExecution):
    def __init__(self, owner, query):
        super().__init__(
            owner.estimator,
            owner.node,
            owner.method,
            owner.bindings,
            owner.stack,
            owner.conditions,
            owner.background,
            query,
        )
        self.elapsed, self.condition = owner.elapsed, owner.condition
        self.variable = self.node.child_by_field_name("left")
        self.kind = "foreach查询输入"

    def projected(self, value, conditions):
        with local_scope(self.estimator, [text(self.variable)], self.bindings) as before:
            state.write(self.estimator.index, self.variable, self.method, self.bindings, value)
            flow = self.estimator.block(
                self.body, self.method, self.bindings, self.stack, conditions, self.background
            )
            for snapshot in flow.states.values():
                restore(snapshot, before)
            return flow
