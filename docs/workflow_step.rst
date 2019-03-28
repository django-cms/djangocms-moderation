.. _workflow_step:

Workflow Step
================================================
Each :ref:`workflow` has at least one :ref:`workflowstep`. These are steps of review the moderation process needs to go through. For example, if an organisation had several different departments, each needing to approve each :ref:`moderation_request`, then:

 1. Each of those departments would be set up as a user Group
 2. A workflow would be created to represent this
 3. A step would be added for each department and the Group for that department would be assigned as the :ref:`role` for that workflow step.

As a result, the draft could not be published without first being approved at each step in the :ref:`workflow`
