const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VadaChainEscrow", function () {
  let Escrow, escrow;
  let owner, client, executor, auditor, stranger;

  beforeEach(async function () {
    [owner, client, executor, auditor, stranger] = await ethers.getSigners();
    Escrow = await ethers.getContractFactory("VadaChainEscrow");
    escrow = await Escrow.deploy();
    await escrow.waitForDeployment();
  });

  describe("Lock Payment", function () {
    it("Should lock payment successfully and emit PaymentLocked event", async function () {
      const taskId = 12345;
      const budget = ethers.parseEther("0.1"); // 0.1 MATIC
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      await expect(
        escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: budget })
      )
        .to.emit(escrow, "PaymentLocked")
        .withArgs(taskId, client.address, executor.address, auditor.address, budget, deadline);

      const task = await escrow.tasks(taskId);
      expect(task.client).to.equal(client.address);
      expect(task.executor).to.equal(executor.address);
      expect(task.auditor).to.equal(auditor.address);
      expect(task.amount).to.equal(budget);
      expect(task.deadline).to.equal(deadline);
      expect(task.resolved).to.be.false;
    });

    it("Should revert if payment is zero", async function () {
      const taskId = 12345;
      const deadline = Math.floor(Date.now() / 1000) + 3600;
      await expect(
        escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: 0 })
      ).to.be.revertedWith("Must send payment");
    });

    it("Should revert if task already exists", async function () {
      const taskId = 12345;
      const budget = ethers.parseEther("0.1");
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      await escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: budget });

      await expect(
        escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: budget })
      ).to.be.revertedWith("Task already exists");
    });
  });

  describe("Submit Verdict", function () {
    const taskId = 12345;
    const budget = ethers.parseEther("1.0");
    let deadline;

    beforeEach(async function () {
      deadline = Math.floor(Date.now() / 1000) + 3600;
      await escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: budget });
    });

    it("Should allow auditor to submit passed verdict, transfer to executor, and update stats", async function () {
      const initialBal = await ethers.provider.getBalance(executor.address);

      await expect(escrow.connect(auditor).submitVerdict(taskId, true))
        .to.emit(escrow, "VerdictSubmitted")
        .withArgs(taskId, true)
        .and.to.emit(escrow, "PaymentReleased")
        .withArgs(taskId, executor.address, budget);

      const finalBal = await ethers.provider.getBalance(executor.address);
      expect(finalBal - initialBal).to.equal(budget);

      const task = await escrow.tasks(taskId);
      expect(task.resolved).to.be.true;

      expect(await escrow.tasksCompleted(executor.address)).to.equal(1);
      expect(await escrow.tasksSucceeded(executor.address)).to.equal(1);
      expect(await escrow.getSuccessRate(executor.address)).to.equal(100);
    });

    it("Should allow auditor to submit failed verdict and refund client", async function () {
      const initialBal = await ethers.provider.getBalance(client.address);

      await expect(escrow.connect(auditor).submitVerdict(taskId, false))
        .to.emit(escrow, "VerdictSubmitted")
        .withArgs(taskId, false)
        .and.to.emit(escrow, "PaymentReleased")
        .withArgs(taskId, client.address, budget);

      const finalBal = await ethers.provider.getBalance(client.address);
      // Client gets refund (ignoring gas since client didn't call submitVerdict, auditor did)
      expect(finalBal - initialBal).to.equal(budget);

      const task = await escrow.tasks(taskId);
      expect(task.resolved).to.be.true;

      expect(await escrow.tasksCompleted(executor.address)).to.equal(1);
      expect(await escrow.tasksSucceeded(executor.address)).to.equal(0);
      expect(await escrow.getSuccessRate(executor.address)).to.equal(0);
    });

    it("CRITICAL: Should revert if submitVerdict is called by non-auditor", async function () {
      // Test that calling submitVerdict from a different wallet (client, stranger, owner) reverts
      await expect(
        escrow.connect(client).submitVerdict(taskId, true)
      ).to.be.revertedWith("Only assigned auditor");

      await expect(
        escrow.connect(stranger).submitVerdict(taskId, true)
      ).to.be.revertedWith("Only assigned auditor");

      await expect(
        escrow.connect(owner).submitVerdict(taskId, true)
      ).to.be.revertedWith("Only assigned auditor");
    });

    it("Should revert if task is already resolved", async function () {
      await escrow.connect(auditor).submitVerdict(taskId, true);
      await expect(
        escrow.connect(auditor).submitVerdict(taskId, true)
      ).to.be.revertedWith("Already resolved");
    });
  });

  describe("Reclaim After Timeout", function () {
    const taskId = 12345;
    const budget = ethers.parseEther("1.0");

    it("Should allow client to reclaim only after deadline", async function () {
      const latestBlock = await ethers.provider.getBlock("latest");
      const deadline = latestBlock.timestamp + 10; // 10 seconds from now
      await escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: budget });

      // Try before deadline -> should revert
      await expect(
        escrow.connect(client).reclaimAfterTimeout(taskId)
      ).to.be.revertedWith("Not yet expired");

      // Fast forward time
      await ethers.provider.send("evm_increaseTime", [15]);
      await ethers.provider.send("evm_mine");

      const initialBal = await ethers.provider.getBalance(client.address);
      const tx = await escrow.connect(client).reclaimAfterTimeout(taskId);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed * receipt.gasPrice;

      const finalBal = await ethers.provider.getBalance(client.address);
      expect(finalBal - initialBal + gasUsed).to.equal(budget);

      const task = await escrow.tasks(taskId);
      expect(task.resolved).to.be.true;
    });

    it("Should revert if non-client attempts to reclaim", async function () {
      const latestBlock = await ethers.provider.getBlock("latest");
      const deadline = latestBlock.timestamp + 10;
      await escrow.connect(client).lockPayment(taskId, executor.address, auditor.address, deadline, { value: budget });

      await ethers.provider.send("evm_increaseTime", [15]);
      await ethers.provider.send("evm_mine");

      await expect(
        escrow.connect(stranger).reclaimAfterTimeout(taskId)
      ).to.be.revertedWith("Only client");
    });
  });
});
