const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying VadaChainEscrow to Polygon Amoy...");

  const [deployer] = await ethers.getSigners();
  console.log(`Deployer address: ${deployer.address}`);
  console.log(`Deployer balance: ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} MATIC`);

  const VadaChainEscrow = await ethers.getContractFactory("VadaChainEscrow");
  const contract = await VadaChainEscrow.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log(`VadaChainEscrow deployed to: ${address}`);

  // Write deployed address to backend/chain/deployed_address.txt
  const outputPath = path.join(__dirname, "../../backend/chain/deployed_address.txt");
  fs.writeFileSync(outputPath, address);
  console.log(`Contract address written to: ${outputPath}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
