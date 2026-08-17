// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VadaChainEscrow
 * @notice Escrow contract for VadaChain multi-agent task payments.
 *         Payment is held until the assigned Auditor agent (and ONLY that auditor)
 *         submits a verdict. This is the core trust guarantee of the system.
 *
 * @dev Key invariant: submitVerdict can ONLY be called by the auditor address
 *      stored at lockPayment time. No backend process, no generic key, no shortcuts.
 */
contract VadaChainEscrow {

    struct Task {
        address client;
        address executor;
        address auditor;
        uint256 amount;
        uint256 deadline;
        bool resolved;
    }

    mapping(uint256 => Task) public tasks;
    mapping(address => uint256) public tasksCompleted;
    mapping(address => uint256) public tasksSucceeded;

    // =====================================================================
    // Events
    // =====================================================================

    event PaymentLocked(
        uint256 indexed taskId,
        address client,
        address executor,
        address auditor,
        uint256 amount,
        uint256 deadline
    );

    event VerdictSubmitted(uint256 indexed taskId, bool passed);

    event PaymentReleased(uint256 indexed taskId, address to, uint256 amount);

    event ReclaimedAfterTimeout(uint256 indexed taskId, address client, uint256 amount);

    // =====================================================================
    // Functions
    // =====================================================================

    /**
     * @notice Lock payment for a task in escrow.
     * @param taskId       Unique task identifier (matches backend TaskSpec.task_id hash)
     * @param executor     Address of the executor agent wallet
     * @param auditor      Address of the auditor agent wallet
     * @param deadline     Unix timestamp after which client can reclaim funds
     */
    function lockPayment(
        uint256 taskId,
        address executor,
        address auditor,
        uint256 deadline
    ) external payable {
        require(tasks[taskId].client == address(0), "Task already exists");
        require(msg.value > 0, "Must send payment");

        tasks[taskId] = Task({
            client: msg.sender,
            executor: executor,
            auditor: auditor,
            amount: msg.value,
            deadline: deadline,
            resolved: false
        });

        emit PaymentLocked(taskId, msg.sender, executor, auditor, msg.value, deadline);
    }

    /**
     * @notice Submit audit verdict. ONLY callable by the auditor address assigned at lock time.
     * @dev    This is the core trust guarantee: msg.sender must equal tasks[taskId].auditor.
     *         No backend shortcut can bypass this on-chain check.
     * @param taskId  The task to resolve
     * @param passed  True → release payment to executor; False → refund to client
     */
    function submitVerdict(uint256 taskId, bool passed) external {
        Task storage t = tasks[taskId];
        require(t.client != address(0), "Task does not exist");
        require(!t.resolved, "Already resolved");
        require(msg.sender == t.auditor, "Only assigned auditor");

        t.resolved = true;
        tasksCompleted[t.executor] += 1;

        emit VerdictSubmitted(taskId, passed);

        if (passed) {
            tasksSucceeded[t.executor] += 1;
            payable(t.executor).transfer(t.amount);
            emit PaymentReleased(taskId, t.executor, t.amount);
        } else {
            payable(t.client).transfer(t.amount);
            emit PaymentReleased(taskId, t.client, t.amount);
        }
    }

    /**
     * @notice Reclaim escrowed funds after deadline if task was never resolved.
     * @dev    Only callable by the original client after deadline has passed.
     * @param taskId  The task to reclaim funds from
     */
    function reclaimAfterTimeout(uint256 taskId) external {
        Task storage t = tasks[taskId];
        require(t.client != address(0), "Task does not exist");
        require(!t.resolved, "Already resolved");
        require(msg.sender == t.client, "Only client");
        require(block.timestamp > t.deadline, "Not yet expired");

        t.resolved = true;
        payable(t.client).transfer(t.amount);
        emit ReclaimedAfterTimeout(taskId, t.client, t.amount);
    }

    /**
     * @notice Get on-chain reputation score (success percentage * 100) for an executor.
     * @param executor  Address to query
     * @return          Success rate as integer (e.g. 85 = 85%)
     */
    function getSuccessRate(address executor) external view returns (uint256) {
        if (tasksCompleted[executor] == 0) return 0;
        return (tasksSucceeded[executor] * 100) / tasksCompleted[executor];
    }
}
